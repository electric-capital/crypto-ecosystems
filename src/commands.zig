const std = @import("std");
const db = @import("taxonomy.zig");
const eql = std.mem.eql;

const Command = enum {
    help,
    version,
    @"export",
    validate,
};

const CommandError = error{
    InvalidCommand,
    MissingArgument,
    InvalidOption,
    MissingOutputPath,
    DuplicateOption,
    EmptyOptionValue,
    OutputAfterOptions,
};

const RunOptions = struct {
    help: bool = false,
    root: ?[]const u8 = null,
    max_date: ?[]const u8 = null,
    ecosystem: ?[]const u8 = null,
    output: ?[]const u8 = null,

    // Validation flags to prevent duplicates
    root_seen: bool = false,
    max_date_seen: bool = false,
    ecosystem_seen: bool = false,
    output_seen: bool = false,
};

const CommandArgs = struct {
    command: Command,
    run_options: ?RunOptions = null,
};

fn printUsage() !void {
    const stdout = std.io.getStdOut().writer();
    try stdout.print(
        \\Usage: ce [-h | --help] <command> [<args>]
        \\
        \\Commands:
        \\  validate                 Validate all of the migrations
        \\      -r, --root DIR       The direction containing the migrations file (default ./migrations)
        \\
        \\  export                   Export the taxonomy to a json file
        \\      -r, --root DIR       The direction containing the migrations file (default ./migrations)
        \\      -e, --ecosystem STR  The name of an ecosystem if you only want to export one
        \\      -m, --max-date STR   The maximum date to run migrations until.
        \\                           One can export the taxonomy state at specific past dates with this param.
        \\      <output>             The output file
        \\
        \\  help                     Show this help message
        \\  version                  Show program version
        \\
    , .{});
}

fn parseRunOptions(command: Command, args: []const []const u8) CommandError!RunOptions {
    var options = RunOptions{};
    var i: usize = 0;

    while (i < args.len) {
        const arg = args[i];

        // Handle empty arguments
        if (arg.len == 0) return CommandError.InvalidOption;

        if (eql(u8, arg, "-h") or eql(u8, arg, "--help")) {
            if (options.help) return CommandError.DuplicateOption;
            options.help = true;
            i += 1;
        } else if (eql(u8, arg, "-r") or eql(u8, arg, "--root")) {
            if (options.root_seen) return CommandError.DuplicateOption;
            options.root_seen = true;

            if (i + 1 >= args.len) return CommandError.MissingArgument;
            const root_path = args[i + 1];

            // Check for empty root path or if it starts with a dash
            if (root_path.len == 0) return CommandError.EmptyOptionValue;
            if (std.mem.startsWith(u8, root_path, "-")) return CommandError.InvalidOption;

            options.root = root_path;
            i += 2;
        } else if (eql(u8, arg, "-m") or eql(u8, arg, "--max-date")) {
            if (options.max_date_seen) return CommandError.DuplicateOption;
            options.max_date_seen = true;

            if (i + 1 >= args.len) return CommandError.MissingArgument;
            const max_date = args[i + 1];

            // Check for empty max_date or if it starts with a dash
            if (max_date.len == 0) return CommandError.EmptyOptionValue;
            if (std.mem.startsWith(u8, max_date, "-")) return CommandError.InvalidOption;

            options.max_date = max_date;
            i += 2;
        } else if (eql(u8, arg, "-e") or eql(u8, arg, "--ecosystem")) {
            if (options.ecosystem_seen) return CommandError.DuplicateOption;
            options.ecosystem_seen = true;

            if (i + 1 >= args.len) return CommandError.MissingArgument;
            const ecosystem = args[i + 1];

            if (ecosystem.len == 0) return CommandError.EmptyOptionValue;
            if (std.mem.startsWith(u8, ecosystem, "-")) return CommandError.InvalidOption;

            options.ecosystem = ecosystem;
            i += 2;
        } else if (std.mem.startsWith(u8, arg, "-")) {
            return CommandError.InvalidOption;
        } else {
            // Treat as output path (positional argument)
            if (options.output_seen) return CommandError.DuplicateOption;
            options.output_seen = true;
            options.output = arg;

            // Check if there are more arguments after output
            if (i + 1 < args.len) return CommandError.OutputAfterOptions;

            i += 1;
        }
    }

    // Only require output if help is not requested
    if (command == .@"export" and !options.output_seen) {
        return CommandError.MissingOutputPath;
    }
    return options;
}

fn parseCommand(args: []const []const u8) CommandError!CommandArgs {
    if (args.len == 0) return CommandError.MissingArgument;

    const cmd_str = args[0];

    const command = if (eql(u8, cmd_str, "help"))
        Command.help
    else if (eql(u8, cmd_str, "version"))
        Command.version
    else if (eql(u8, cmd_str, "validate"))
        Command.validate
    else if (eql(u8, cmd_str, "export"))
        Command.@"export"
    else
        return CommandError.InvalidCommand;

    if (command == .validate or command == .@"export") {
        const run_options = try parseRunOptions(command, args[1..]);
        return CommandArgs{
            .command = command,
            .run_options = run_options,
        };
    }

    if (args.len > 1) return CommandError.InvalidOption;

    return CommandArgs{
        .command = command,
        .run_options = null,
    };
}

fn printVersion() !void {
    const stdout = std.io.getStdOut().writer();
    try stdout.writeAll("2.0\n");
}

fn executeCommand(a: std.mem.Allocator, cmd: CommandArgs) !void {
    switch (cmd.command) {
        .help => try printUsage(),
        .version => try printVersion(),
        .@"export" => try cmdExport(a, cmd.run_options.?),
        .validate => try cmdValidate(a, cmd.run_options.?),
    }
}

pub fn cmdMain(allocator: std.mem.Allocator) !void {
    const args = try std.process.argsAlloc(allocator);
    defer std.process.argsFree(allocator, args);

    if (args.len < 2) {
        try printUsage();
        return;
    }

    const cmd = parseCommand(args[1..]) catch |err| {
        switch (err) {
            error.MissingOutputPath => {
                std.debug.print("Please specify an output path for export\n\n", .{});
            },
            else => {},
        }
        try printUsage();
        return;
    };
    if (cmd.run_options) |opts| {
        if (opts.help) {
            try printUsage();
            return;
        }
    }
    try executeCommand(allocator, cmd);
}

pub fn cmdValidate(gpa: std.mem.Allocator, options: RunOptions) !void {
    const default_dir = try defaultMigrationsPath(gpa);
    defer gpa.free(default_dir);

    const root = options.root orelse default_dir;
    var taxonomy = db.Taxonomy.init(gpa);
    defer taxonomy.deinit();
    const load_result = try taxonomy.load(root, null);
    _ = load_result;

    const stats = taxonomy.stats();

    const magenta = "\x1b[35m";
    const reset = "\x1b[0m";

    var stdout = std.io.getStdOut().writer();
    try stdout.print("{s}┃{s} {d:<6} Migrations\n", .{ magenta, reset, stats.migration_count });
    try stdout.print("{s}┃{s} {d:<6} Ecosystems\n", .{ magenta, reset, stats.eco_count });
    try stdout.print("{s}┃{s} {d:<6} Repos\n", .{ magenta, reset, stats.repo_count });
    try stdout.print("{s}┃{s} {d:<6} Tags\n", .{ magenta, reset, stats.tag_count });
}

fn defaultMigrationsPath(a: std.mem.Allocator) ![]const u8 {
    return try std.fs.cwd().realpathAlloc(a, "migrations");
}

pub fn cmdExport(gpa: std.mem.Allocator, options: RunOptions) !void {
    const default_dir = try defaultMigrationsPath(gpa);
    defer gpa.free(default_dir);

    const root = options.root orelse default_dir;
    var taxonomy = db.Taxonomy.init(gpa);
    defer taxonomy.deinit();
    const load_result = try taxonomy.load(root, options.max_date);
    _ = load_result;
    if (options.output) |output| {
        try taxonomy.exportJson(output, options.ecosystem);
    }
}
