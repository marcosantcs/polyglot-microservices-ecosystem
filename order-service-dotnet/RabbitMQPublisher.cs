using System.Text;
using System.Text.Json;
using RabbitMQ.Client;
using Microsoft.Extensions.Options;

namespace OrderService.Infrastructure.Messaging;

public class RabbitMQSettings
{
    public string Host     { get; set; } = "localhost";
    public int    Port     { get; set; } = 5672;
    public string Username { get; set; } = "guest";
    public string Password { get; set; } = "guest";
    public string Exchange { get; set; } = "orders.exchange";
}

/// <summary>
/// Resilient RabbitMQ publisher.
/// Uses a single persistent channel with automatic reconnect on failure.
/// </summary>
public class RabbitMQPublisher : IAsyncDisposable
{
    private readonly RabbitMQSettings _settings;
    private readonly ILogger<RabbitMQPublisher> _logger;
    private IConnection? _connection;
    private IModel?      _channel;

    public RabbitMQPublisher(IOptions<RabbitMQSettings> settings, ILogger<RabbitMQPublisher> logger)
    {
        _settings = settings.Value;
        _logger   = logger;
    }

    private void EnsureConnected()
    {
        if (_connection?.IsOpen == true && _channel?.IsOpen == true) return;

        var factory = new ConnectionFactory
        {
            HostName = _settings.Host,
            Port     = _settings.Port,
            UserName = _settings.Username,
            Password = _settings.Password,
            // Enable automatic recovery from network failures
            AutomaticRecoveryEnabled = true,
            NetworkRecoveryInterval  = TimeSpan.FromSeconds(5)
        };

        _connection = factory.CreateConnection("order-service");
        _channel    = _connection.CreateModel();

        // Declare a topic exchange — supports wildcard routing keys
        _channel.ExchangeDeclare(
            exchange: _settings.Exchange,
            type:     ExchangeType.Topic,
            durable:  true,
            autoDelete: false
        );

        // Dead-letter queue for failed messages
        var dlqArgs = new Dictionary<string, object>
        {
            ["x-dead-letter-exchange"] = $"{_settings.Exchange}.dlx"
        };

        _channel.QueueDeclare(queue: "orders.created",   durable: true, exclusive: false, autoDelete: false, arguments: dlqArgs);
        _channel.QueueDeclare(queue: "orders.cancelled", durable: true, exclusive: false, autoDelete: false, arguments: dlqArgs);
        _channel.QueueBind("orders.created",   _settings.Exchange, "order.created");
        _channel.QueueBind("orders.cancelled", _settings.Exchange, "order.cancelled");

        _logger.LogInformation("RabbitMQ connection established to {Host}", _settings.Host);
    }

    /// <summary>Serialize and publish a message to the exchange with the given routing key.</summary>
    public Task PublishAsync(string routingKey, object message)
    {
        try
        {
            EnsureConnected();

            var json  = JsonSerializer.Serialize(message, new JsonSerializerOptions { WriteIndented = false });
            var body  = Encoding.UTF8.GetBytes(json);

            var props = _channel!.CreateBasicProperties();
            props.Persistent    = true;       // survive broker restart
            props.ContentType   = "application/json";
            props.MessageId     = Guid.NewGuid().ToString();
            props.Timestamp     = new AmqpTimestamp(DateTimeOffset.UtcNow.ToUnixTimeSeconds());

            _channel.BasicPublish(
                exchange:   _settings.Exchange,
                routingKey: routingKey,
                basicProperties: props,
                body:       body
            );

            _logger.LogInformation("Event published — routing key: {RoutingKey}, messageId: {MessageId}",
                routingKey, props.MessageId);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to publish message with routing key {RoutingKey}", routingKey);
            throw;
        }

        return Task.CompletedTask;
    }

    public async ValueTask DisposeAsync()
    {
        _channel?.Close();
        _connection?.Close();
        await Task.CompletedTask;
    }
}
