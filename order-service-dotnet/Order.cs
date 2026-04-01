using System;
using System.Collections.Generic;

namespace OrderService.Domain.Entities;

public class OrderStatus
{
    public static readonly OrderStatus Pending   = new("pending");
    public static readonly OrderStatus Confirmed = new("confirmed");
    public static readonly OrderStatus Shipped   = new("shipped");
    public static readonly OrderStatus Cancelled = new("cancelled");

    public string Value { get; private set; }
    private OrderStatus(string value) => Value = value;
    public override string ToString() => Value;
}

public class OrderItem
{
    public Guid       Id        { get; private set; }
    public string     Product   { get; private set; }
    public int        Quantity  { get; private set; }
    public decimal    UnitPrice { get; private set; }
    public decimal    Total     => Quantity * UnitPrice;

    private OrderItem() { }

    public static OrderItem Create(string product, int quantity, decimal unitPrice)
    {
        if (string.IsNullOrWhiteSpace(product)) throw new ArgumentException("Product name is required.");
        if (quantity <= 0)   throw new ArgumentException("Quantity must be greater than zero.");
        if (unitPrice <= 0)  throw new ArgumentException("Unit price must be greater than zero.");

        return new OrderItem
        {
            Id        = Guid.NewGuid(),
            Product   = product,
            Quantity  = quantity,
            UnitPrice = unitPrice
        };
    }
}

/// <summary>
/// Rich Domain Entity — encapsulates all business rules for an Order.
/// Follows DDD: state changes only via domain methods, invariants enforced internally.
/// </summary>
public class Order
{
    private readonly List<OrderItem> _items = new();

    public Guid              Id          { get; private set; }
    public string            CustomerId  { get; private set; }
    public OrderStatus       Status      { get; private set; }
    public DateTime          CreatedAt   { get; private set; }
    public DateTime?         UpdatedAt   { get; private set; }
    public IReadOnlyList<OrderItem> Items => _items.AsReadOnly();
    public decimal           TotalAmount => _items.Sum(i => i.Total);

    // EF Core requires parameterless constructor
    private Order() { }

    // Factory method — only valid way to create an Order
    public static Order Create(string customerId)
    {
        if (string.IsNullOrWhiteSpace(customerId))
            throw new ArgumentException("CustomerId is required.");

        return new Order
        {
            Id         = Guid.NewGuid(),
            CustomerId = customerId,
            Status     = OrderStatus.Pending,
            CreatedAt  = DateTime.UtcNow
        };
    }

    public void AddItem(string product, int quantity, decimal unitPrice)
    {
        if (Status != OrderStatus.Pending)
            throw new InvalidOperationException("Items can only be added to Pending orders.");

        _items.Add(OrderItem.Create(product, quantity, unitPrice));
        Touch();
    }

    public void Confirm()
    {
        if (Status != OrderStatus.Pending)
            throw new InvalidOperationException("Only Pending orders can be confirmed.");
        if (!_items.Any())
            throw new InvalidOperationException("Cannot confirm an order with no items.");

        Status = OrderStatus.Confirmed;
        Touch();
    }

    public void Cancel(string reason)
    {
        if (Status == OrderStatus.Shipped)
            throw new InvalidOperationException("Cannot cancel a shipped order.");

        Status = OrderStatus.Cancelled;
        Touch();
    }

    private void Touch() => UpdatedAt = DateTime.UtcNow;
}
