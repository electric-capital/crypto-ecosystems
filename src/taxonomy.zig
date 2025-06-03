const std = @import("std");
const shlex = @import("./shlex.zig");
const timestamp = @import("./timestamp.zig");
const print = std.debug.print;

const assert = std.debug.assert;
const ArrayList = std.ArrayList;
const HashMap = std.hash_map.HashMap;
const AutoHashMap = std.hash_map.AutoHashMap;

const SliceIdMap = HashMap([]const u8, u32, std.hash_map.StringContext, std.hash_map.default_max_load_percentage);
const IdSliceMap = AutoHashMap(u32, []const u8);

const IdSet = AutoHashMap(u32, void);
const RepoSet = AutoHashMap(u32, void);
const EcoToRepoMap = AutoHashMap(u32, RepoSet);
const RepoToEcoMap = AutoHashMap(u32, u32);
const ParentToChildMap = AutoHashMap(u32, IdSet);
const ChildToParentMap = AutoHashMap(u32, IdSet);

const EcoTagKey = struct { eco_id: u32, repo_id: u32 };
const EcoRepoToTagMap = AutoHashMap(EcoTagKey, IdSet);

pub const TaxonomyStats = struct {
    migration_count: u32,
    eco_count: u32,
    repo_count: u32,
    eco_connections_count: u32,
    tag_count: u32,
};

pub const TaxonomyError = struct {
    message: []const u8,
    line_num: u32,
    path: []const u8,
};

pub const TaxonomyLoadResult = struct { errors: ArrayList(TaxonomyError) };

pub const Ecosystem = struct {
    id: u32,
    name: []const u8,
    sub_ecosystems: []const []const u8,
    repos: []const []const u8,

    pub fn deinit(self: *Ecosystem, allocator: std.mem.Allocator) void {
        allocator.free(self.repos);
        allocator.free(self.sub_ecosystems);
    }
};

pub const EcosystemRepoRowJson = struct {
    const Self = @This();
    eco_name: []const u8,
    branch: []const []const u8,
    repo_url: []const u8,
    tags: []const []const u8,

    pub fn deinit(self: *Self, allocator: std.mem.Allocator) void {
        allocator.free(self.branch);
        allocator.free(self.tags);
    }
};

pub const Taxonomy = struct {
    allocator: std.mem.Allocator,
    eco_auto_id: u32,
    repo_auto_id: u32,
    tag_auto_id: u32,
    migration_count: u32,

    buffers: ArrayList([]const u8),

    eco_ids: SliceIdMap,
    repo_ids: SliceIdMap,
    tag_ids: SliceIdMap,
    tag_id_to_name_map: IdSliceMap,
    repo_id_to_url_map: IdSliceMap,
    eco_id_to_name_map: IdSliceMap,
    eco_to_repo_map: EcoToRepoMap,
    repo_to_eco_map: RepoToEcoMap,
    parent_to_child_map: ParentToChildMap,
    child_to_parent_map: ChildToParentMap,
    eco_repo_to_tag_map: EcoRepoToTagMap,
    errors: ArrayList(TaxonomyError),

    pub fn init(allocator: std.mem.Allocator) Taxonomy {
        return .{
            .allocator = allocator,
            .eco_auto_id = 0,
            .repo_auto_id = 0,
            .tag_auto_id = 0,
            .migration_count = 0,
            .buffers = ArrayList([]const u8).init(allocator),
            .eco_ids = SliceIdMap.init(allocator),
            .repo_ids = SliceIdMap.init(allocator),
            .tag_ids = SliceIdMap.init(allocator),
            .tag_id_to_name_map = IdSliceMap.init(allocator),
            .parent_to_child_map = ParentToChildMap.init(allocator),
            .child_to_parent_map = ChildToParentMap.init(allocator),
            .eco_to_repo_map = EcoToRepoMap.init(allocator),
            .repo_to_eco_map = RepoToEcoMap.init(allocator),
            .repo_id_to_url_map = IdSliceMap.init(allocator),
            .eco_id_to_name_map = IdSliceMap.init(allocator),
            .eco_repo_to_tag_map = EcoRepoToTagMap.init(allocator),
            .errors = ArrayList(TaxonomyError).init(allocator),
        };
    }

    pub fn deinit(self: *Taxonomy) void {
        var iterator = self.eco_to_repo_map.iterator();
        while (iterator.next()) |entry| {
            entry.value_ptr.deinit();
        }

        var p2c_iterator = self.parent_to_child_map.iterator();
        while (p2c_iterator.next()) |entry| {
            entry.value_ptr.deinit();
        }
        var c2p_iterator = self.child_to_parent_map.iterator();
        while (c2p_iterator.next()) |entry| {
            entry.value_ptr.deinit();
        }

        var tag_set_iterator = self.eco_repo_to_tag_map.iterator();
        while (tag_set_iterator.next()) |entry| {
            entry.value_ptr.deinit();
        }

        self.parent_to_child_map.deinit();
        self.child_to_parent_map.deinit();
        self.eco_to_repo_map.deinit();
        self.tag_ids.deinit();
        self.tag_id_to_name_map.deinit();
        self.eco_ids.deinit();
        self.repo_ids.deinit();
        self.repo_id_to_url_map.deinit();
        self.repo_to_eco_map.deinit();
        self.eco_id_to_name_map.deinit();
        self.eco_repo_to_tag_map.deinit();

        self.errors.deinit();

        for (self.buffers.items) |buf| {
            self.allocator.free(buf);
        }
        self.buffers.deinit();
    }

    /// The max_date parameter filters out any migrations that occur after a
    /// particular date.
    pub fn load(self: *Taxonomy, root: []const u8, max_date_: ?[]const u8) !void {
        var dir = try std.fs.cwd().openDir(root, .{ .iterate = true });
        defer dir.close();

        // Create directory iterator
        var iter = dir.iterate();

        var path_buf: [std.fs.max_path_bytes]u8 = undefined;

        var migration_files = std.ArrayList([]const u8).init(self.allocator);
        defer {
            for (migration_files.items) |filename| {
                self.allocator.free(filename);
            }
            migration_files.deinit();
        }

        while (try iter.next()) |entry| {
            if (entry.kind == std.fs.File.Kind.file) {
                const name = try self.allocator.dupe(u8, entry.name);
                if (timestamp.hasValidTimestamp(name)) {
                    if (max_date_) |max_date| {
                        if (std.mem.lessThan(u8, name, max_date)) {
                            try migration_files.append(name);
                        } else {
                            self.allocator.free(name);
                        }
                    } else {
                        try migration_files.append(name);
                    }
                } else {
                    self.allocator.free(name);
                }
            }
        }

        std.mem.sort([]const u8, migration_files.items, {}, struct {
            pub fn lessThan(_: void, a: []const u8, b: []const u8) bool {
                return std.mem.lessThan(u8, a[0..19], b[0..19]);
            }
        }.lessThan);

        var fba = std.heap.FixedBufferAllocator.init(&path_buf);
        const fba_allocator = fba.allocator();
        for (migration_files.items) |filename| {
            fba.reset();
            const full_path = try std.fs.path.join(fba_allocator, &.{ root, filename });
            try self.loadFile(full_path);
            self.migration_count += 1;
        }

        if (self.hasErrors()) {
            self.printErrors();
            return error.ValidationFailed;
        }
    }

    fn loadFile(self: *Taxonomy, path: []const u8) !void {
        const file = try std.fs.cwd().openFile(path, .{});
        defer file.close();

        const size = try file.getEndPos();
        const buffer = try self.allocator.alloc(u8, size);

        // One big read
        _ = try file.readAll(buffer);
        try self.buffers.append(buffer);

        var iter = std.mem.splitScalar(u8, buffer, '\n');
        var line_num: u32 = 0;

        while (iter.next()) |line| {
            line_num += 1;

            if (isComment(line)) {
                continue;
            }
            // Note: line might end in \r for CRLF files
            //std.debug.print("{s}\n", .{line});
            if (line.len < 6) {
                continue;
            }

            const keyword = line[0..6];
            const remainder = line[6..];

            const result = if (keyword[0] == 'r' and std.mem.eql(u8, keyword, "repadd"))
                repAdd(remainder, self)
            else if (std.mem.eql(u8, keyword, "ecocon"))
                ecoCon(remainder, self)
            else if (std.mem.eql(u8, keyword, "ecoadd"))
                ecoAdd(remainder, self)
            else if (std.mem.eql(u8, keyword, "ecodis"))
                ecoDis(remainder, self)
            else if (std.mem.eql(u8, keyword, "ecorem"))
                ecoRem(remainder, self)
            else if (std.mem.eql(u8, keyword, "repmov"))
                repMov(remainder, self)
            else if (std.mem.eql(u8, keyword, "ecomov"))
                ecoMov(remainder, self)
            else if (std.mem.eql(u8, keyword, "reprem"))
                repRem(remainder, self);
            
            result catch |err| {
                try self.errors.append(.{
                    .message = @errorName(err),
                    .line_num = line_num,
                    .path = path,
                });
            };
        }
    }

    pub fn hasErrors(self: *Taxonomy) bool {
        return self.errors.items.len > 0;
    }

    pub fn printErrors(self: *Taxonomy) void {
        for (self.errors.items) |err| {
            std.debug.print("{s}:{}: error.{s}\n", .{ err.path, err.line_num, err.message  });
        }
    }

    pub fn stats(self: *Taxonomy) TaxonomyStats {
        return .{
            .migration_count = self.migration_count,
            .eco_count = self.eco_ids.count(),
            .repo_count = self.repo_ids.count(),
            .eco_connections_count = 0,
            .tag_count = self.tag_ids.count(),
        };
    }

    fn tagStringsForEcoRepo(self: *Taxonomy, a: std.mem.Allocator, eco_id: u32, repo_id: u32) !?[][]const u8 {
        const key: EcoTagKey = .{ .eco_id = eco_id, .repo_id = repo_id };
        if (self.eco_repo_to_tag_map.get(key)) |tag_ids| {
            const tag_strs = try a.alloc([]const u8, tag_ids.count());
            var i: u32 = 0;
            var tag_id_it = tag_ids.keyIterator();
            while (tag_id_it.next()) |tag_id| {
                const tag_str = self.tag_id_to_name_map.get(tag_id.*).?;
                tag_strs[i] = tag_str;
                i += 1;
            }
            return tag_strs;
        } else {
            return null;
        }
    }

    fn emitEcosystemJson(self: *Taxonomy, writer: anytype, top: []const u8, branch: *ArrayList([]const u8), eco_id: u32) !void {
        var arena = std.heap.ArenaAllocator.init(std.heap.page_allocator);
        defer arena.deinit();

        const IdStrTuple = struct { id: u32, str: []const u8 };
        const lessThanLowercaseTuple = struct {
            fn inner(_: void, a: IdStrTuple, b: IdStrTuple) bool {
                return std.ascii.lessThanIgnoreCase(a.str, b.str);
            }
        }.inner;

        const allocator = arena.allocator();
        const repo_ids = self.eco_to_repo_map.get(eco_id);
        const repo_tuples = if (repo_ids) |ids| ok: {
            const repo_tuples = try allocator.alloc(IdStrTuple, ids.count());
            var repo_id_it = ids.keyIterator();
            var i: u32 = 0;
            while (repo_id_it.next()) |repo_id| {
                repo_tuples[i] = .{
                    .id = repo_id.*,
                    .str = self.repo_id_to_url_map.get(repo_id.*).?,
                };
                i += 1;
            }
            std.mem.sort(IdStrTuple, repo_tuples, {}, lessThanLowercaseTuple);
            break :ok repo_tuples;
        } else ko: {
            break :ko &[_]IdStrTuple{};
        };

        for (repo_tuples) |tup| {
            const tag_strs = try self.tagStringsForEcoRepo(allocator, eco_id, tup.id);
            const row = EcosystemRepoRowJson{
                .eco_name = top,
                .branch = branch.items,
                .repo_url = tup.str,
                .tags = tag_strs orelse &[_][]const u8{},
            };
            try std.json.stringify(row, .{}, writer);
            try writer.writeByte('\n');
        }

        const sub_ids_ = self.parent_to_child_map.get(eco_id);
        const sub_tuples = if (sub_ids_) |sub_ids| ok: {
            const sub_tuples = try allocator.alloc(IdStrTuple, sub_ids.count());
            var sub_id_it = sub_ids.keyIterator();
            var i: u32 = 0;
            while (sub_id_it.next()) |sub_eco_id| {
                sub_tuples[i] = .{
                    .id = sub_eco_id.*,
                    .str = self.eco_id_to_name_map.get(sub_eco_id.*).?,
                };
                i += 1;
            }
            std.mem.sort(IdStrTuple, sub_tuples, {}, lessThanLowercaseTuple);
            break :ok sub_tuples;
        } else ko: {
            break :ko &[_]IdStrTuple{};
        };

        for (sub_tuples) |tup| {
            try branch.append(tup.str);
            try self.emitEcosystemJson(writer, top, branch, tup.id);
            _ = branch.pop();
        }
    }

    /// param: ecosystem -- Specify a single ecosystem
    pub fn exportJson(self: *Taxonomy, output_file: []const u8, ecosystem: ?[]const u8) !void {
        const KeyPair = struct { eco_name: []const u8, eco_id: u32 };

        var keys_list = try std.ArrayList(KeyPair).initCapacity(self.allocator, self.eco_ids.count());
        defer keys_list.deinit();

        var iterator = self.eco_ids.iterator();
        if (ecosystem) |only| {
            const eco_id_pair = self.eco_ids.getEntry(only);
            if (eco_id_pair) |eco_pair| {
                try keys_list.append(.{ .eco_name = eco_pair.key_ptr.*, .eco_id = eco_pair.value_ptr.* });
            } else {
                return error.InvalidEcosystem;
            }
        } else {
            while (iterator.next()) |entry| {
                try keys_list.append(.{ .eco_name = entry.key_ptr.*, .eco_id = entry.value_ptr.* });
            }
            std.mem.sort(
                KeyPair,
                keys_list.items,
                {},
                struct {
                    fn lessThan(_: void, a: KeyPair, b: KeyPair) bool {
                        return std.ascii.lessThanIgnoreCase(a.eco_name, b.eco_name);
                    }
                }.lessThan,
            );
        }

        const file = try std.fs.cwd().createFile(output_file, .{ .read = false, .truncate = true });
        defer file.close();

        var buffered_writer = std.io.bufferedWriter(file.writer());
        const writer = buffered_writer.writer();

        var branch = ArrayList([]const u8).init(self.allocator);
        defer branch.deinit();
        for (keys_list.items) |item| {
            try self.emitEcosystemJson(writer, item.eco_name, &branch, item.eco_id);
        }

        try buffered_writer.flush();
    }

    pub fn eco(self: *Taxonomy, name: []const u8) !?Ecosystem {
        const eco_id = self.eco_ids.get(name) orelse return null;
        const repo_ids = self.eco_to_repo_map.get(eco_id);
        const repo_urls = if (repo_ids) |ids| ok: {
            const repo_urls = try self.allocator.alloc([]const u8, ids.count());
            var iterator = ids.keyIterator();
            var i: u32 = 0;
            while (iterator.next()) |repo_id| {
                repo_urls[i] = self.repo_id_to_url_map.get(repo_id.*).?;
                i += 1;
            }
            std.mem.sort([]const u8, repo_urls, {}, lessThanLowercase);
            break :ok repo_urls;
        } else ko: {
            break :ko &[_][]const u8{};
        };

        const sub_ids = self.parent_to_child_map.get(eco_id);
        const sub_ecosystem_names = if (sub_ids) |sub_id_set| ok: {
            var sub_names = try self.allocator.alloc([]const u8, sub_id_set.count());
            var iterator = sub_id_set.keyIterator();
            var i: u32 = 0;
            while (iterator.next()) |sub_id| {
                sub_names[i] = self.eco_id_to_name_map.get(sub_id.*).?;
                i += 1;
            }
            std.mem.sort([]const u8, sub_names, {}, lessThanLowercase);
            break :ok sub_names;
        } else ko: {
            break :ko &[_][]const u8{};
        };
        return .{
            .id = eco_id,
            .name = name,
            .repos = repo_urls,
            .sub_ecosystems = sub_ecosystem_names,
        };
    }

    fn addEco(self: *Taxonomy, name: []const u8) !void {
        const eco_id_entry = try self.eco_ids.getOrPut(name);
        if (!eco_id_entry.found_existing) {
            self.eco_auto_id += 1;
            eco_id_entry.value_ptr.* = self.eco_auto_id;
            try self.eco_id_to_name_map.putNoClobber(self.eco_auto_id, name);
        }
    }

    /// Connecting an eco creates an entry in both the parent -> child_set map
    /// and the child -> parent_set map for book keeping
    fn connectEco(self: *Taxonomy, parent: []const u8, child: []const u8) !void {
        const parent_id = self.eco_ids.get(parent) orelse return error.InvalidParentEcosystem;
        const child_id = self.eco_ids.get(child) orelse return error.InvalidChildEcosystem;
        const child_entry = try self.parent_to_child_map.getOrPut(parent_id);
        if (!child_entry.found_existing) {
            child_entry.value_ptr.* = IdSet.init(self.allocator);
        }
        try child_entry.value_ptr.put(child_id, {});

        const parent_entry = try self.child_to_parent_map.getOrPut(child_id);
        if (!parent_entry.found_existing) {
            parent_entry.value_ptr.* = IdSet.init(self.allocator);
        }
        try parent_entry.value_ptr.put(parent_id, {});
    }

    fn disconnectEco(self: *Taxonomy, parent: []const u8, child: []const u8) !void {
        const parent_id = self.eco_ids.get(parent) orelse return error.InvalidParentEcosystem;
        const child_id = self.eco_ids.get(child) orelse return error.InvalidChildEcosystem;

        var child_set = self.parent_to_child_map.getPtr(parent_id) orelse return error.ParentEcosystemHasNoChildren;
        _ = child_set.remove(child_id);

        if (self.child_to_parent_map.getPtr(child_id)) |parent_set| {
            _ = parent_set.remove(parent_id);
        }
    }

    fn removeEcoById(self: *Taxonomy, eco_id: u32) void {
        const parent_set = self.child_to_parent_map.getPtr(eco_id);
        if (parent_set) |ps| {
            var parent_id_it = ps.keyIterator();
            while (parent_id_it.next()) |parent_id| {
                if (self.parent_to_child_map.getPtr(parent_id.*)) |child_set| {
                    const removed = child_set.remove(eco_id);
                    assert(removed);
                }
            }
            ps.*.clearAndFree();
            const removed = self.child_to_parent_map.remove(eco_id);
            assert(removed);
        }

        if (self.parent_to_child_map.getPtr(eco_id)) |child_set| {
            child_set.*.clearAndFree();
            const removed = self.parent_to_child_map.remove(eco_id);
            assert(removed);
        }
    }

    /// The removal operation is a bit tricky.  It does the following
    /// - removes the eco from its parents
    /// - clears the repos from the ecosystem itself
    /// - removes the children ecosystem connections (but leaves the children intact)
    /// - destroys the ecosystem
    fn removeEco(self: *Taxonomy, eco_name: []const u8) !void {
        const eco_id = self.eco_ids.get(eco_name) orelse return error.InvalidEcosystem;
        self.removeEcoById(eco_id);

        const removed = self.eco_ids.remove(eco_name);
        assert(removed);
    }

    fn addRepo(self: *Taxonomy, eco_name: []const u8, repo_url: []const u8, tags_: ?[]?[]const u8) !void {
        const eco_id = self.eco_ids.get(eco_name) orelse return error.InvalidEcosystem;
        const repo_id_entry = try self.repo_ids.getOrPut(repo_url);
        if (!repo_id_entry.found_existing) {
            self.repo_auto_id += 1;
            repo_id_entry.value_ptr.* = self.repo_auto_id;
            try self.repo_id_to_url_map.putNoClobber(self.repo_auto_id, repo_url);
        } else {}
        const repo_id = repo_id_entry.value_ptr.*;

        const repos_for_eco_entry = try self.eco_to_repo_map.getOrPut(eco_id);
        if (!repos_for_eco_entry.found_existing) {
            repos_for_eco_entry.value_ptr.* = RepoSet.init(self.allocator);
        }
        var repo_set = repos_for_eco_entry.value_ptr;
        // TODO let's potentially add error handling if duplicate repos are in the mutations,
        // but it doesn't hurt to add the same repo twice.
        try repo_set.put(repo_id, {});
        if (tags_) |tags| {
            for (tags) |tag| {
                const tag_entry = try self.tag_ids.getOrPut(tag.?);
                if (!tag_entry.found_existing) {
                    self.tag_auto_id += 1;
                    tag_entry.value_ptr.* = self.tag_auto_id;
                    try self.tag_id_to_name_map.putNoClobber(self.tag_auto_id, tag.?);
                }
                const tag_id = tag_entry.value_ptr.*;
                const key: EcoTagKey = .{ .eco_id = eco_id, .repo_id = repo_id };
                const tag_map_entry = try self.eco_repo_to_tag_map.getOrPut(key);
                if (!tag_map_entry.found_existing) {
                    tag_map_entry.value_ptr.* = IdSet.init(self.allocator);
                }
                const tag_set = tag_map_entry.value_ptr;
                try tag_set.put(tag_id, {});
            }
        }
    }

    fn moveRepo(self: *Taxonomy, src: []const u8, dst: []const u8) !void {
        const src_id = self.repo_ids.get(src) orelse return error.InvalidSourceRepo;
        if (self.repo_ids.contains(dst)) {
            return error.DestinationRepoAlreadyExists;
        }
        _ = self.repo_ids.remove(src);
        try self.repo_id_to_url_map.put(src_id, dst);
        try self.repo_ids.put(dst, src_id);
    }

    fn moveEco(self: *Taxonomy, src: []const u8, dst: []const u8) !void {
        const src_id = self.eco_ids.get(src) orelse return error.InvalidSourceEcosystem;
        if (self.eco_ids.contains(dst)) {
            return error.DestinationEcosystemAlreadyExists;
        }
        _ = self.eco_ids.remove(src);
        try self.eco_id_to_name_map.put(src_id, dst);
        try self.eco_ids.put(dst, src_id);
    }

    fn removeRepoFromEcosystem(self: *Taxonomy, eco_name: []const u8, repo: []const u8) !void {
        const eco_id = self.eco_ids.get(eco_name) orelse return error.InvalidEcosystem;
        var repos_for_eco = self.eco_to_repo_map.getPtr(eco_id) orelse return error.EcosystemHasNoRepos;
        const repo_id = self.repo_ids.get(repo) orelse return error.InvalidRepo;
        _ = repos_for_eco.remove(repo_id);

        const key: EcoTagKey = .{ .eco_id = eco_id, .repo_id = repo_id };
        const tagMapPtr_ = self.eco_repo_to_tag_map.getPtr(key);
        if (tagMapPtr_) |tagMapPtr| {
            tagMapPtr.deinit();
            _ = self.eco_repo_to_tag_map.remove(key);
        }
    }
};

/// Returns whether  a line is a comment
fn isComment(line: []const u8) bool {
    var i: usize = 0;
    while (i < line.len) {
        // Skip whitespace
        while (i < line.len and std.ascii.isWhitespace(line[i])) i += 1;
        if (i >= line.len) break;
        if (line[i] == '#') {
            return true;
        } else {
            return false;
        }
    }
    return false;
}

fn ecoAdd(sub_line: []const u8, db: *Taxonomy) !void {
    var tokens: [10]?[]const u8 = undefined;
    const token_count = try shlex.split(sub_line, &tokens);
    if (token_count != 1) {
        return error.EcoAddRequiresOneParameter;
    }

    if (tokens[0]) |token| {
        try db.addEco(token);
    }
}

/// Connect an ecosystem to another ecosystem
fn ecoCon(sub_line: []const u8, db: *Taxonomy) !void {
    var tokens: [10]?[]const u8 = undefined;
    const token_count = try shlex.split(sub_line, &tokens);
    if (token_count != 2) {
        return error.EcoConRequiresExactlyTwoParameters;
    }

    if (tokens[0] != null and tokens[1] != null) {
        const parent = tokens[0].?;
        const child = tokens[1].?;
        try db.connectEco(parent, child);
    }
}

/// Disconnect an ecosystem from another one.
fn ecoDis(sub_line: []const u8, db: *Taxonomy) !void {
    var tokens: [2]?[]const u8 = undefined;
    const token_count = try shlex.split(sub_line, &tokens);
    if (token_count != 2) {
        return error.EcoDisRequiresExactlyTwoParameters;
    }

    if (tokens[0] != null and tokens[1] != null) {
        const parent = tokens[0].?;
        const child = tokens[1].?;
        try db.disconnectEco(parent, child);
    }
}

/// Remove ecosystems
fn ecoRem(sub_line: []const u8, db: *Taxonomy) !void {
    var tokens: [1]?[]const u8 = undefined;
    const token_count = try shlex.split(sub_line, &tokens);
    if (token_count != 1) {
        return error.EcoRemRequiresExactlyTwoParameters;
    }

    if (tokens[0] != null) {
        const eco = tokens[0].?;
        try db.removeEco(eco);
    }
}

fn repAdd(remainder: []const u8, db: *Taxonomy) !void {
    var tokens: [10]?[]const u8 = undefined;
    const token_count = try shlex.split(remainder, &tokens);
    if (token_count < 2) {
        return error.RepAddRequiresAtLeastTwoParameters;
    }

    if (tokens[0] != null and tokens[1] != null) {
        const eco = tokens[0].?;
        const repo = tokens[1].?;
        const tags = if (token_count > 2) tokens[2..token_count] else null;
        try db.addRepo(eco, repo, tags);
    }
}

/// Rename a repo
fn repMov(remainder: []const u8, db: *Taxonomy) !void {
    var tokens: [2]?[]const u8 = undefined;
    const token_count = try shlex.split(remainder, &tokens);
    if (token_count != 2) {
        return error.RepMovRequiresExactlyTwoParameters;
    }

    if (tokens[0] != null and tokens[1] != null) {
        const src = tokens[0].?;
        const dst = tokens[1].?;
        try db.moveRepo(src, dst);
    }
}

fn ecoMov(remainder: []const u8, db: *Taxonomy) !void {
    var tokens: [2]?[]const u8 = undefined;
    const token_count = try shlex.split(remainder, &tokens);
    if (token_count != 2) {
        return error.EcoMovRequiresExactlyTwoParameters;
    }

    if (tokens[0] != null and tokens[1] != null) {
        const src = tokens[0].?;
        const dst = tokens[1].?;
        try db.moveEco(src, dst);
    }
}

fn repRem(remainder: []const u8, db: *Taxonomy) !void {
    var tokens: [2]?[]const u8 = undefined;
    const token_count = try shlex.split(remainder, &tokens);
    if (token_count != 2) {
        return error.RepRemRequiresExactlyTwoParameters;
    }

    if (tokens[0] != null and tokens[1] != null) {
        const eco = tokens[0].?;
        const repo = tokens[1].?;
        try db.removeRepoFromEcosystem(eco, repo);
    }
}

fn lessThanLowercase(_: void, a: []const u8, b: []const u8) bool {
    var i: usize = 0;
    while (i < @min(a.len, b.len)) : (i += 1) {
        const a_lower = std.ascii.toLower(a[i]);
        const b_lower = std.ascii.toLower(b[i]);
        if (a_lower != b_lower) {
            return a_lower < b_lower;
        }
    }
    return a.len < b.len;
}

/// Tests Below
fn getTestsPath(a: std.mem.Allocator, testDir: []const u8) ![]u8 {
    const build_dir = try findBuildZigDirAlloc(a);
    defer a.free(build_dir);

    const tests_path = try std.fs.path.join(a, &.{ build_dir, "tests", testDir });
    return tests_path;
}

fn setupTestFixtures(testDir: []const u8) !Taxonomy {
    const a = std.testing.allocator;
    const tests_path = try getTestsPath(a, testDir);

    defer a.free(tests_path);

    var db = Taxonomy.init(a);
    try db.load(tests_path, null);

    return db;
}

/// This function finds the root of the project so that unit tests
/// can find the test fixtures directory.
fn findBuildZigDirAlloc(allocator: std.mem.Allocator) ![]const u8 {
    const self_path = try std.fs.selfExePathAlloc(allocator);
    defer allocator.free(self_path);

    var current_path = std.fs.path.dirname(self_path) orelse "/";

    while (true) {
        const build_path = try std.fs.path.join(allocator, &.{ current_path, "build.zig" });
        defer allocator.free(build_path);

        std.fs.accessAbsolute(build_path, .{}) catch |err| {
            if (err == error.FileNotFound) {
                if (current_path.len == 0 or std.mem.eql(u8, current_path, "/")) {
                    return error.BuildZigNotFound;
                }
                current_path = std.fs.path.dirname(current_path) orelse "/";
                continue;
            }
            return err;
        };

        return allocator.dupe(u8, current_path);
    }
}

// Unit tests of the taxonomy loader.
test "load of single ecosystem" {
    const testing = std.testing;
    const a = testing.allocator;

    var db = try setupTestFixtures("simple_ecosystems");
    defer db.deinit();
    const stats = db.stats();

    try testing.expectEqual(1, stats.migration_count);
    try testing.expectEqual(1, stats.eco_count);
    try testing.expectEqual(3, stats.repo_count);
    try testing.expectEqual(1, stats.tag_count);
    var btc = (try db.eco("Bitcoin")).?;
    defer btc.deinit(a);

    try testing.expectEqualStrings("Bitcoin", btc.name);
    try testing.expectEqual(1, btc.id);
    try testing.expectEqual(3, btc.repos.len);
    try testing.expectEqualStrings("https://github.com/bitcoin/bips", btc.repos[0]);
}

test "time ordering" {
    const testing = std.testing;
    const a = testing.allocator;

    var db = try setupTestFixtures("time_ordering");
    defer db.deinit();
    const stats = db.stats();

    try testing.expectEqual(3, stats.migration_count);
    try testing.expectEqual(1, stats.eco_count);
    try testing.expectEqual(2, stats.repo_count);

    var eth = (try db.eco("Ethereum")).?;
    try testing.expectEqual(2, eth.repos.len);
    try testing.expectEqualStrings("https://github.com/ethereum/aleth", eth.repos[0]);
    try testing.expectEqualStrings("https://github.com/openethereum/parity-ethereum", eth.repos[1]);
    defer eth.deinit(a);
}

test "ecosystem disconnect" {
    const testing = std.testing;
    const a = testing.allocator;
    var db = try setupTestFixtures("ecosystem_disconnect");
    defer db.deinit();
    const stats = db.stats();

    try testing.expectEqual(2, stats.migration_count);
    try testing.expectEqual(5, stats.eco_count);
    try testing.expectEqual(1, stats.repo_count);

    var poly = (try db.eco("Polygon")).?;
    defer poly.deinit(a);
    try testing.expectEqual(1, poly.sub_ecosystems.len);
    try testing.expectEqualStrings("DeGods", poly.sub_ecosystems[0]);
    var solana = (try db.eco("Solana")).?;
    defer solana.deinit(a);

    try testing.expectEqual(0, solana.sub_ecosystems.len);
}

test "ecosystem rename" {
    const testing = std.testing;
    const a = testing.allocator;
    var db = try setupTestFixtures("ecosystem_rename");
    defer db.deinit();
    const stats = db.stats();

    try testing.expectEqual(1, stats.migration_count);
    try testing.expectEqual(2, stats.eco_count);
    try testing.expectEqual(2, stats.repo_count);

    var multi = (try db.eco("MultiversX")).?;
    defer multi.deinit(a);
    try testing.expectEqual(1, multi.sub_ecosystems.len);

    const elrond = try db.eco("Elrond");
    try testing.expectEqual(null, elrond);
}

test "repo removals" {
    const testing = std.testing;
    const a = testing.allocator;
    var db = try setupTestFixtures("repo_removals");
    defer db.deinit();
    const stats = db.stats();

    try testing.expectEqual(2, stats.migration_count);
    try testing.expectEqual(2, stats.eco_count);
    try testing.expectEqual(6, stats.repo_count);

    var eth = (try db.eco("Ethereum")).?;
    defer eth.deinit(a);
    try testing.expectEqual(1, eth.repos.len);
}

test "ecosystem removal" {
    const testing = std.testing;
    const a = testing.allocator;

    var db = try setupTestFixtures("ecosystem_removal");
    defer db.deinit();
    const stats = db.stats();

    try testing.expectEqual(1, stats.migration_count);
    try testing.expectEqual(5, stats.eco_count);
    try testing.expectEqual(2, stats.repo_count);

    const me = try db.eco("Magic Eden");
    try testing.expectEqual(null, me);

    var btc = (try db.eco("Bitcoin")).?;
    defer btc.deinit(a);
    try testing.expectEqual(0, btc.sub_ecosystems.len);

    var me_wallet = try db.eco("Magic Eden Wallet");
    try testing.expect(me_wallet != null);
    me_wallet.?.deinit(a);
}

test "date filtering" {
    const testing = std.testing;
    const a = testing.allocator;

    const tests_path = try getTestsPath(a, "date_filtering");
    defer a.free(tests_path);

    {
        var db = Taxonomy.init(a);
        try db.load(tests_path, "2011");
        defer db.deinit();

        const stats = db.stats();
        try testing.expectEqual(1, stats.migration_count);
        try testing.expectEqual(1, stats.eco_count);
    }
    {
        var db = Taxonomy.init(a);
        try db.load(tests_path, "2013");
        defer db.deinit();

        const stats = db.stats();
        try testing.expectEqual(2, stats.migration_count);
        try testing.expectEqual(2, stats.eco_count);
    }
    {
        var db = Taxonomy.init(a);
        try db.load(tests_path, "2015-08-01");
        defer db.deinit();

        const stats = db.stats();
        try testing.expectEqual(3, stats.migration_count);
        try testing.expectEqual(3, stats.eco_count);
    }
}

test "json export" {
    const testing = std.testing;
    const a = testing.allocator;
    var db = try setupTestFixtures("tiered");
    defer db.deinit();

    var multi = (try db.eco("Bitcoin")).?;
    defer multi.deinit(a);
    try testing.expectEqual(1, multi.sub_ecosystems.len);

    var tmp = std.testing.tmpDir(.{});
    defer tmp.cleanup();

    const dir_path = try tmp.dir.realpathAlloc(a, ".");
    defer a.free(dir_path);

    const file_path = try std.fs.path.join(a, &.{ dir_path, "export.json" });
    defer a.free(file_path);

    try db.exportJson(file_path, null);

    const content = try tmp.dir.readFileAlloc(testing.allocator, file_path, std.math.maxInt(usize));
    defer testing.allocator.free(content);

    const expected =
        \\{"eco_name":"Bitcoin","branch":[],"repo_url":"https://github.com/bitcoin/bitcoin","tags":["#protocol"]}
        \\{"eco_name":"Bitcoin","branch":["Lightning"],"repo_url":"https://github.com/lightningnetwork/lnd","tags":["#protocol"]}
        \\{"eco_name":"Bitcoin","branch":["Lightning","Lightspark"],"repo_url":"https://github.com/lightsparkdev/lightspark-rs","tags":["#sdk"]}
        \\{"eco_name":"Lightning","branch":[],"repo_url":"https://github.com/lightningnetwork/lnd","tags":["#protocol"]}
        \\{"eco_name":"Lightning","branch":["Lightspark"],"repo_url":"https://github.com/lightsparkdev/lightspark-rs","tags":["#sdk"]}
        \\{"eco_name":"Lightspark","branch":[],"repo_url":"https://github.com/lightsparkdev/lightspark-rs","tags":["#sdk"]}
        \\
    ;

    try testing.expectEqualStrings(expected, content);
}

// When emitting just the Lightning ecosystem it should show the lightning repos as well as the branch containing LightSpark
test "json export of single ecosystem" {
    const testing = std.testing;
    const a = testing.allocator;
    var db = try setupTestFixtures("tiered");
    defer db.deinit();

    var tmp = std.testing.tmpDir(.{});
    defer tmp.cleanup();

    const dir_path = try tmp.dir.realpathAlloc(a, ".");
    defer a.free(dir_path);

    const file_path = try std.fs.path.join(a, &.{ dir_path, "lightning.json" });
    defer a.free(file_path);

    try db.exportJson(file_path, "Lightning");

    const content = try tmp.dir.readFileAlloc(testing.allocator, file_path, std.math.maxInt(usize));
    defer testing.allocator.free(content);

    const expected =
        \\{"eco_name":"Lightning","branch":[],"repo_url":"https://github.com/lightningnetwork/lnd","tags":["#protocol"]}
        \\{"eco_name":"Lightning","branch":["Lightspark"],"repo_url":"https://github.com/lightsparkdev/lightspark-rs","tags":["#sdk"]}
        \\
    ;

    try testing.expectEqualStrings(expected, content);
}
