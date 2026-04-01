using Microsoft.AspNetCore.Mvc;
using OrderService.Domain.Entities;
using OrderService.Infrastructure.Messaging;

namespace OrderService.API.Controllers;

[ApiController]
[Route("api/[controller]")]
public class OrderController : ControllerBase
{
    private readonly RabbitMQPublisher _publisher;
    private readonly ILogger<OrderController> _logger;

    // In a real project this would use a repository/service layer
    private static readonly List<Order> _store = new();

    public OrderController(RabbitMQPublisher publisher, ILogger<OrderController> logger)
    {
        _publisher = publisher;
        _logger    = logger;
    }

    /// <summary>GET /api/order — list all orders</summary>
    [HttpGet]
    public IActionResult GetAll() => Ok(_store.Select(o => new
    {
        o.Id, o.CustomerId, Status = o.Status.ToString(),
        o.TotalAmount, o.CreatedAt, ItemCount = o.Items.Count
    }));

    /// <summary>GET /api/order/{id}</summary>
    [HttpGet("{id:guid}")]
    public IActionResult GetById(Guid id)
    {
        var order = _store.FirstOrDefault(o => o.Id == id);
        return order is null ? NotFound() : Ok(order);
    }

    /// <summary>POST /api/order — create an order and publish event</summary>
    [HttpPost]
    public async Task<IActionResult> Create([FromBody] CreateOrderRequest request)
    {
        try
        {
            var order = Order.Create(request.CustomerId);

            foreach (var item in request.Items)
                order.AddItem(item.Product, item.Quantity, item.UnitPrice);

            order.Confirm();
            _store.Add(order);

            // Publish domain event to RabbitMQ
            await _publisher.PublishAsync("order.created", new
            {
                OrderId    = order.Id,
                CustomerId = order.CustomerId,
                Status     = order.Status.ToString(),
                Total      = order.TotalAmount,
                Items      = order.Items.Select(i => new { i.Product, i.Quantity, i.UnitPrice }),
                Timestamp  = DateTime.UtcNow
            });

            _logger.LogInformation("Order {OrderId} created and event published.", order.Id);
            return CreatedAtAction(nameof(GetById), new { id = order.Id }, order);
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new { error = ex.Message });
        }
    }

    /// <summary>DELETE /api/order/{id} — cancel an order</summary>
    [HttpDelete("{id:guid}")]
    public async Task<IActionResult> Cancel(Guid id, [FromBody] CancelOrderRequest request)
    {
        var order = _store.FirstOrDefault(o => o.Id == id);
        if (order is null) return NotFound();

        try
        {
            order.Cancel(request.Reason);

            await _publisher.PublishAsync("order.cancelled", new
            {
                OrderId   = order.Id,
                Reason    = request.Reason,
                Timestamp = DateTime.UtcNow
            });

            return NoContent();
        }
        catch (InvalidOperationException ex)
        {
            return Conflict(new { error = ex.Message });
        }
    }
}

// ── DTOs ─────────────────────────────────────────────────────────────────────
public record CreateOrderItemDto(string Product, int Quantity, decimal UnitPrice);
public record CreateOrderRequest(string CustomerId, List<CreateOrderItemDto> Items);
public record CancelOrderRequest(string Reason);
