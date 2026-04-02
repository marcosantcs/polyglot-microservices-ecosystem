using System;
using System.Linq;
using Xunit;
using OrderService.Domain.Entities;

namespace OrderService.Tests;

public class OrderTests
{
    // ── Order.Create ──────────────────────────────────────────────────────────
    [Fact]
    public void Create_ValidCustomerId_ReturnsOrderWithPendingStatus()
    {
        var order = Order.Create("customer-1");
        Assert.Equal("pending", order.Status.ToString());
        Assert.Equal("customer-1", order.CustomerId);
        Assert.NotEqual(Guid.Empty, order.Id);
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    [InlineData(null)]
    public void Create_InvalidCustomerId_ThrowsArgumentException(string customerId)
    {
        Assert.Throws<ArgumentException>(() => Order.Create(customerId));
    }

    // ── AddItem ───────────────────────────────────────────────────────────────
    [Fact]
    public void AddItem_ValidItem_IncreasesTotalAmount()
    {
        var order = Order.Create("customer-1");
        order.AddItem("Notebook", 2, 4500m);
        Assert.Equal(9000m, order.TotalAmount);
        Assert.Single(order.Items);
    }

    [Fact]
    public void AddItem_MultipleItems_AccumulatesTotal()
    {
        var order = Order.Create("customer-1");
        order.AddItem("Notebook", 1, 4500m);
        order.AddItem("Mouse",    2,  150m);
        Assert.Equal(4800m, order.TotalAmount);
        Assert.Equal(2, order.Items.Count);
    }

    [Fact]
    public void AddItem_ToConfirmedOrder_ThrowsInvalidOperationException()
    {
        var order = Order.Create("customer-1");
        order.AddItem("Notebook", 1, 4500m);
        order.Confirm();
        Assert.Throws<InvalidOperationException>(() => order.AddItem("Mouse", 1, 150m));
    }

    [Theory]
    [InlineData("", 1, 100)]
    [InlineData("Item", 0, 100)]
    [InlineData("Item", 1, 0)]
    public void AddItem_InvalidParameters_ThrowsArgumentException(string product, int qty, decimal price)
    {
        var order = Order.Create("customer-1");
        Assert.Throws<ArgumentException>(() => order.AddItem(product, qty, price));
    }

    // ── Confirm ───────────────────────────────────────────────────────────────
    [Fact]
    public void Confirm_PendingOrderWithItems_ChangesStatusToConfirmed()
    {
        var order = Order.Create("customer-1");
        order.AddItem("Notebook", 1, 4500m);
        order.Confirm();
        Assert.Equal("confirmed", order.Status.ToString());
        Assert.NotNull(order.UpdatedAt);
    }

    [Fact]
    public void Confirm_OrderWithNoItems_ThrowsInvalidOperationException()
    {
        var order = Order.Create("customer-1");
        Assert.Throws<InvalidOperationException>(() => order.Confirm());
    }

    [Fact]
    public void Confirm_AlreadyConfirmedOrder_ThrowsInvalidOperationException()
    {
        var order = Order.Create("customer-1");
        order.AddItem("Notebook", 1, 4500m);
        order.Confirm();
        Assert.Throws<InvalidOperationException>(() => order.Confirm());
    }

    // ── Cancel ────────────────────────────────────────────────────────────────
    [Fact]
    public void Cancel_PendingOrder_ChangesStatusToCancelled()
    {
        var order = Order.Create("customer-1");
        order.AddItem("Notebook", 1, 4500m);
        order.Cancel("Customer request");
        Assert.Equal("cancelled", order.Status.ToString());
    }

    [Fact]
    public void Cancel_ConfirmedOrder_ChangesStatusToCancelled()
    {
        var order = Order.Create("customer-1");
        order.AddItem("Notebook", 1, 4500m);
        order.Confirm();
        order.Cancel("Changed mind");
        Assert.Equal("cancelled", order.Status.ToString());
    }

    [Fact]
    public void Cancel_ShippedOrder_ThrowsInvalidOperationException()
    {
        // Shipped status cannot be cancelled — domain invariant
        var order = Order.Create("customer-1");
        order.AddItem("Notebook", 1, 4500m);
        order.Confirm();
        // Simulate shipped via reflection (no public method intentionally)
        var statusField = typeof(Order).GetProperty("Status",
            System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance);
        statusField!.SetValue(order, OrderStatus.Shipped);
        Assert.Throws<InvalidOperationException>(() => order.Cancel("Too late"));
    }
}

public class OrderItemTests
{
    [Fact]
    public void Create_ValidParams_ReturnsCorrectTotal()
    {
        var item = OrderItem.Create("Notebook", 3, 4500m);
        Assert.Equal(13500m, item.Total);
        Assert.Equal("Notebook", item.Product);
        Assert.NotEqual(Guid.Empty, item.Id);
    }

    [Fact]
    public void Create_NegativeQuantity_ThrowsArgumentException()
        => Assert.Throws<ArgumentException>(() => OrderItem.Create("X", -1, 10m));

    [Fact]
    public void Create_ZeroUnitPrice_ThrowsArgumentException()
        => Assert.Throws<ArgumentException>(() => OrderItem.Create("X", 1, 0m));
}
