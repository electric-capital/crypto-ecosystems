const std = @import("std");
const commands = @import("commands.zig");

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    try commands.cmdMain(allocator);
}

test {
    std.testing.refAllDecls(@This());
}
