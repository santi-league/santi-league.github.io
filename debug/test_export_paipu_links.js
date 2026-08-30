#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
    OUTPUT_PREFIX,
    TARGET_CONTEST_ID,
    TARGET_CONTEST_UNIQUE_ID,
    buildPaipuUrl,
    createWebSocketProxy,
    decodeCustomizedContestLookupResponse,
    decodeGameRecordListResponse,
    decodeGameRecordListV2Response,
    decodeNextGameRecordListResponse,
    decodeRecordListRequest,
    extractUuidsFromBytes,
    filterRecords,
    hookWebSocketPrototype,
    mergeRecords,
    normalizeRecord,
    recordTypeFromV2Tag,
    serializeLinks,
} = require("../src/download_paipu/export_paipu_links.user.js");

const UUID_OLD = "260829-a4c57245-fead-416d-b46a-1ed20fd33ed8";
const UUID_NEW = "260830-5b83d443-9c8e-4447-a162-d485fd35377f";
function concatBytes(...chunks) {
    const length = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
    const result = new Uint8Array(length);
    let offset = 0;
    for (const chunk of chunks) {
        result.set(chunk, offset);
        offset += chunk.length;
    }
    return result;
}

function varint(value) {
    let remaining = BigInt(value);
    const bytes = [];
    do {
        let byte = Number(remaining & 0x7fn);
        remaining >>= 7n;
        if (remaining) {
            byte |= 0x80;
        }
        bytes.push(byte);
    } while (remaining);
    return Uint8Array.from(bytes);
}

function fieldVarint(number, value) {
    return concatBytes(varint(number << 3), varint(value));
}

function fieldBytes(number, value) {
    const bytes = typeof value === "string" ? new TextEncoder().encode(value) : value;
    return concatBytes(varint((number << 3) | 2), varint(bytes.length), bytes);
}

function wrapper(name, data) {
    return concatBytes(fieldBytes(1, name), fieldBytes(2, data));
}

function account(accountId, seat, nickname) {
    return concatBytes(
        fieldVarint(1, accountId),
        fieldVarint(2, seat),
        fieldBytes(3, nickname),
    );
}

function contestInfo(uniqueId, contestId, contestName) {
    return concatBytes(
        fieldVarint(1, uniqueId),
        fieldVarint(2, contestId),
        fieldBytes(3, contestName),
    );
}

function record({ uuid, startTime, endTime, contestUniqueId, nickname }) {
    const meta = fieldVarint(3, contestUniqueId);
    const config = concatBytes(fieldVarint(1, 4), fieldBytes(3, meta));
    return concatBytes(
        fieldBytes(1, uuid),
        fieldVarint(2, startTime),
        fieldVarint(3, endTime),
        fieldBytes(5, config),
        fieldBytes(11, account(12345, 0, nickname)),
    );
}

function recordPlayer(accountId, seat, nickname) {
    return concatBytes(
        fieldVarint(2, accountId),
        fieldBytes(3, nickname),
        fieldVarint(6, seat),
    );
}

function recordListEntry({ uuid, startTime, endTime, tag, subtag, nickname }) {
    return concatBytes(
        fieldVarint(1, 1),
        fieldBytes(2, uuid),
        fieldVarint(3, startTime),
        fieldVarint(4, endTime),
        fieldVarint(5, tag),
        fieldVarint(6, subtag),
        fieldBytes(7, recordPlayer(54321, 1, nickname)),
        fieldVarint(8, 1),
    );
}

class FakeWebSocket {
    constructor(url) {
        this.url = url;
        this.listeners = new Map();
        this.sent = [];
    }

    addEventListener(type, listener) {
        if (!this.listeners.has(type)) {
            this.listeners.set(type, []);
        }
        this.listeners.get(type).push(listener);
    }

    send(data) {
        this.sent.push(data);
    }

    emit(type, data) {
        for (const listener of this.listeners.get(type) || []) {
            listener({ data });
        }
    }
}

test("生成与现有下载脚本兼容的无视角链接", () => {
    assert.equal(TARGET_CONTEST_ID, 866_461);
    assert.equal(TARGET_CONTEST_UNIQUE_ID, 20_808_476);
    assert.equal(
        buildPaipuUrl(UUID_NEW),
        `https://game.maj-soul.com/1/?paipu=${UUID_NEW}`,
    );
    assert.throws(() => buildPaipuUrl("not-a-uuid"), /无效的牌谱 UUID/);
});

test("links.txt 每行都有分隔前缀，并按 UUID 去重", () => {
    const text = serializeLinks([
        { uuid: UUID_OLD, endTime: 100 },
        { uuid: UUID_NEW, endTime: 200 },
        { uuid: UUID_OLD, endTime: 100 },
    ]);
    assert.equal(
        text,
        `${OUTPUT_PREFIX}https://game.maj-soul.com/1/?paipu=${UUID_NEW}\n`
        + `${OUTPUT_PREFIX}https://game.maj-soul.com/1/?paipu=${UUID_OLD}\n`,
    );
});

test("只从二进制内容提取严格格式 UUID", () => {
    const payload = new TextEncoder().encode(`x${UUID_OLD}y ${UUID_NEW.toUpperCase()} broken-uuid`);
    assert.deepEqual(extractUuidsFromBytes(payload), [UUID_OLD, UUID_NEW]);
});

test("解析 fetchGameRecordList 请求的分页和类型字段", () => {
    const request = concatBytes(fieldVarint(1, 1), fieldVarint(2, 30), fieldVarint(3, 4));
    assert.deepEqual(
        decodeRecordListRequest(wrapper(".lq.Lobby.fetchGameRecordList", request)),
        { kind: "v1-list", method: ".lq.Lobby.fetchGameRecordList", start: 1, count: 30, type: 4 },
    );
    assert.equal(decodeRecordListRequest(wrapper(".lq.Lobby.fetchGameRecord", request)), null);
});

test("区分 V2 游标、公开比赛场查询和内部赛事牌谱请求", () => {
    const startRequest = concatBytes(
        fieldVarint(1, 4),
        fieldVarint(2, 1_777_000_000),
        fieldVarint(3, 1_777_200_000),
    );
    assert.deepEqual(
        decodeRecordListRequest(wrapper(".lq.Lobby.fetchGameRecordListV2", startRequest)),
        {
            kind: "v2-start",
            method: ".lq.Lobby.fetchGameRecordListV2",
            tag: 4,
            type: 4,
            beginTime: 1_777_000_000,
            endTime: 1_777_200_000,
        },
    );
    assert.equal(recordTypeFromV2Tag(1), 2, "V2 RANK 应归一化为段位战");
    assert.equal(recordTypeFromV2Tag(2), 1, "V2 FRIEND 应归一化为友人战");
    assert.deepEqual(
        decodeRecordListRequest(wrapper(
            ".lq.Lobby.fetchNextGameRecordList",
            concatBytes(fieldBytes(1, "iterator-123"), fieldVarint(2, 30)),
        )),
        {
            kind: "v2-next",
            method: ".lq.Lobby.fetchNextGameRecordList",
            iterator: "iterator-123",
            count: 30,
        },
    );
    assert.deepEqual(
        decodeRecordListRequest(wrapper(".lq.Lobby.fetchGameRecordsDetailV2", fieldBytes(1, UUID_NEW))),
        { kind: "v2-detail", method: ".lq.Lobby.fetchGameRecordsDetailV2" },
    );
    assert.deepEqual(
        decodeRecordListRequest(wrapper(
            ".lq.Lobby.fetchCustomizedContestByContestId",
            fieldVarint(1, TARGET_CONTEST_ID),
        )),
        {
            kind: "contest-lookup",
            method: ".lq.Lobby.fetchCustomizedContestByContestId",
            contestId: TARGET_CONTEST_ID,
        },
    );
    assert.deepEqual(
        decodeRecordListRequest(wrapper(
            ".lq.Lobby.fetchCustomizedContestGameRecords",
            concatBytes(fieldVarint(1, TARGET_CONTEST_UNIQUE_ID), fieldVarint(2, 40)),
        )),
        {
            kind: "contest-list",
            method: ".lq.Lobby.fetchCustomizedContestGameRecords",
            contestUniqueId: TARGET_CONTEST_UNIQUE_ID,
            lastIndex: 40,
            type: 4,
        },
    );
});

test("从公开比赛场查询响应解析内部 unique_id", () => {
    const response = wrapper(
        ".lq.ResFetchCustomizedContestByContestId",
        fieldBytes(2, contestInfo(TARGET_CONTEST_UNIQUE_ID, TARGET_CONTEST_ID, "Santi League")),
    );
    assert.deepEqual(decodeCustomizedContestLookupResponse(response), {
        uniqueId: TARGET_CONTEST_UNIQUE_ID,
        contestId: TARGET_CONTEST_ID,
        contestName: "Santi League",
    });
});

test("从列表响应解析牌谱、赛事 ID 和玩家信息", () => {
    const first = record({
        uuid: UUID_OLD,
        startTime: 1_777_000_000,
        endTime: 1_777_001_000,
        contestUniqueId: TARGET_CONTEST_UNIQUE_ID,
        nickname: "santi",
    });
    const second = record({
        uuid: UUID_NEW,
        startTime: 1_777_100_000,
        endTime: 1_777_101_000,
        contestUniqueId: TARGET_CONTEST_UNIQUE_ID,
        nickname: "DreamKQ",
    });
    const response = concatBytes(
        fieldVarint(2, 2),
        fieldBytes(3, first),
        fieldBytes(3, second),
    );
    const decoded = decodeGameRecordListResponse(
        wrapper(".lq.ResGameRecordList", response),
        4,
    );

    assert.equal(decoded.length, 2);
    assert.deepEqual(decoded[0], {
        uuid: UUID_OLD,
        startTime: 1_777_000_000,
        endTime: 1_777_001_000,
        requestType: 4,
        category: 4,
        roomId: 0,
        contestId: 0,
        contestUniqueId: TARGET_CONTEST_UNIQUE_ID,
        accounts: [{ accountId: 12345, seat: 0, nickname: "santi" }],
    });
});

test("列表中单条元数据损坏时仍保留其严格 UUID", () => {
    const valid = record({
        uuid: UUID_OLD,
        startTime: 1_777_000_000,
        endTime: 1_777_001_000,
        contestUniqueId: TARGET_CONTEST_UNIQUE_ID,
        nickname: "santi",
    });
    const malformed = concatBytes(Uint8Array.of(0), new TextEncoder().encode(UUID_NEW));
    const decoded = decodeGameRecordListResponse(wrapper(
        ".lq.ResGameRecordList",
        concatBytes(fieldBytes(3, valid), fieldBytes(3, malformed)),
    ), 4);
    assert.deepEqual(decoded.map((item) => item.uuid), [UUID_OLD, UUID_NEW]);
});

test("解析 V2 游标响应和 RecordListEntry", () => {
    const iteratorResponse = decodeGameRecordListV2Response(wrapper(
        ".lq.ResGameRecordListV2",
        concatBytes(
            fieldBytes(2, "iterator-123"),
            fieldVarint(3, 1_777_300_000),
            fieldVarint(4, 1_777_000_000),
            fieldVarint(5, 1_777_200_000),
        ),
    ));
    assert.deepEqual(iteratorResponse, {
        iterator: "iterator-123",
        iteratorExpire: 1_777_300_000,
        actualBeginTime: 1_777_000_000,
        actualEndTime: 1_777_200_000,
    });

    const nextResponse = decodeNextGameRecordListResponse(wrapper(
        ".lq.ResNextGameRecordList",
        concatBytes(
            fieldVarint(2, 0),
            fieldBytes(3, recordListEntry({
                uuid: UUID_NEW,
                startTime: 1_777_100_000,
                endTime: 1_777_101_000,
                tag: 4,
                subtag: 20_808_476,
                nickname: "DreamKQ",
            })),
            fieldVarint(4, 1_777_300_000),
        ),
    ), 4);
    assert.equal(nextResponse.hasNext, false);
    assert.deepEqual(nextResponse.records[0], {
        uuid: UUID_NEW,
        startTime: 1_777_100_000,
        endTime: 1_777_101_000,
        requestType: 4,
        category: 4,
        roomId: 0,
        contestId: 0,
        contestUniqueId: 0,
        accounts: [{ accountId: 54321, seat: 1, nickname: "DreamKQ" }],
    });
});

test("当前 record_map 的 V2 对象可回退归一化", () => {
    assert.deepEqual(normalizeRecord({
        version: 1,
        uuid: UUID_NEW,
        start_time: 1_777_100_000,
        end_time: 1_777_101_000,
        tag: 1,
        subtag: 20_808_476,
        players: [{ account_id: 54321, seat: 1, nickname: "DreamKQ" }],
        standard_rule: 1,
    }), {
        uuid: UUID_NEW,
        startTime: 1_777_100_000,
        endTime: 1_777_101_000,
        requestType: 2,
        category: 2,
        roomId: 0,
        contestId: 0,
        contestUniqueId: 0,
        accounts: [{ accountId: 54321, seat: 1, nickname: "DreamKQ" }],
    });
});

test("WebSocket 代理只捕获与列表请求 ID 对应的响应，且不修改流量", () => {
    const captures = [];
    const HookedWebSocket = createWebSocketProxy(
        FakeWebSocket,
        (records, request) => captures.push({ records, request }),
    );
    const socket = new HookedWebSocket("wss://example.test/gateway");
    class ChildWebSocket extends HookedWebSocket {}
    const childSocket = new ChildWebSocket("wss://example.test/child");
    assert.equal(childSocket instanceof ChildWebSocket, true);
    assert.equal(childSocket instanceof FakeWebSocket, true);
    const requestBody = concatBytes(fieldVarint(1, 1), fieldVarint(2, 30), fieldVarint(3, 4));
    const requestFrame = concatBytes(
        Uint8Array.of(2, 0x34, 0x12),
        wrapper(".lq.Lobby.fetchGameRecordList", requestBody),
    );
    const padded = concatBytes(Uint8Array.of(9, 9), requestFrame, Uint8Array.of(9));
    const requestView = padded.subarray(2, padded.length - 1);
    socket.send(requestView);

    const responseBody = concatBytes(
        fieldVarint(2, 1),
        fieldBytes(3, record({
            uuid: UUID_NEW,
            startTime: 1_777_100_000,
            endTime: 1_777_101_000,
            contestUniqueId: TARGET_CONTEST_UNIQUE_ID,
            nickname: "santi",
        })),
    );
    const responseFrame = concatBytes(
        Uint8Array.of(3, 0x34, 0x12),
        wrapper(".lq.ResGameRecordList", responseBody),
    );
    socket.emit("message", responseFrame);
    socket.emit("message", responseFrame); // pending id was consumed; must not capture twice

    const contestRequest = concatBytes(
        Uint8Array.of(2, 0x35, 0x12),
        wrapper(
            ".lq.Lobby.fetchCustomizedContestGameRecords",
            concatBytes(fieldVarint(1, 20_808_476), fieldVarint(2, 0)),
        ),
    );
    socket.send(contestRequest);
    socket.emit("message", concatBytes(
        Uint8Array.of(3, 0x35, 0x12),
        wrapper(".lq.ResFetchCustomizedContestGameRecords", concatBytes(
            fieldVarint(2, 0),
            fieldBytes(3, record({
                uuid: UUID_OLD,
                startTime: 1_777_000_000,
                endTime: 1_777_001_000,
                contestUniqueId: 0,
                nickname: "DreamKQ",
            })),
        )),
    ));

    assert.equal(socket.sent.length, 2);
    assert.equal(socket.sent[0], requestView);
    assert.equal(socket.sent[1], contestRequest);
    assert.equal(captures.length, 2);
    assert.equal(captures[0].request.type, 4);
    assert.equal(captures[0].records[0].uuid, UUID_NEW);
    assert.equal(captures[1].request.kind, "contest-list");
    assert.equal(captures[1].records[0].contestId, 0);
    assert.equal(captures[1].records[0].contestUniqueId, TARGET_CONTEST_UNIQUE_ID);
});

test("WebSocket 原构造器被 Unity 提前保存或实例已创建时仍能捕获", () => {
    class CapturedWebSocket extends FakeWebSocket {}
    const UnitySavedWebSocket = CapturedWebSocket;
    const socket = new UnitySavedWebSocket("wss://example.test/gateway");
    const captures = [];
    const hook = hookWebSocketPrototype(
        CapturedWebSocket,
        (records, request) => captures.push({ records, request }),
        () => {},
        {
            targetContestId: TARGET_CONTEST_ID,
            initialContestMappings: [{
                uniqueId: TARGET_CONTEST_UNIQUE_ID,
                contestId: TARGET_CONTEST_ID,
            }],
        },
    );

    try {
        const requestFrame = concatBytes(
            Uint8Array.of(2, 0x36, 0x12),
            wrapper(
                ".lq.Lobby.fetchCustomizedContestGameRecords",
                concatBytes(fieldVarint(1, TARGET_CONTEST_UNIQUE_ID), fieldVarint(2, 0)),
            ),
        );
        socket.send(requestFrame);
        socket.emit("message", concatBytes(
            Uint8Array.of(3, 0x36, 0x12),
            wrapper(".lq.ResFetchCustomizedContestGameRecords", fieldBytes(3, record({
                uuid: UUID_NEW,
                startTime: 1_777_100_000,
                endTime: 1_777_101_000,
                contestUniqueId: TARGET_CONTEST_UNIQUE_ID,
                nickname: "santi",
            }))),
        ));

        assert.deepEqual(socket.sent, [requestFrame]);
        assert.equal(socket.listeners.get("message").length, 1);
        assert.equal(captures.length, 1);
        assert.equal(captures[0].request.contestId, TARGET_CONTEST_ID);
        assert.equal(captures[0].records[0].contestUniqueId, TARGET_CONTEST_UNIQUE_ID);
        assert.equal(captures[0].records[0].uuid, UUID_NEW);
    } finally {
        hook.restore();
    }
});

test("监听器或诊断回调失败时仍原样发送游戏流量", () => {
    class ListenerFailureWebSocket {
        constructor() {
            this.sent = [];
        }

        addEventListener() {
            throw new Error("listener unavailable");
        }

        send(data) {
            this.sent.push(data);
            return "native-result";
        }
    }

    const originalDescriptor = Object.getOwnPropertyDescriptor(
        ListenerFailureWebSocket.prototype,
        "send",
    );
    const hook = hookWebSocketPrototype(
        ListenerFailureWebSocket,
        () => {},
        () => { throw new Error("diagnostic failure"); },
    );
    const socket = new ListenerFailureWebSocket();
    const payload = Uint8Array.of(2, 1, 0, 0);

    try {
        assert.equal(socket.send(payload), "native-result");
        assert.equal(socket.send(payload), "native-result");
        assert.deepEqual(socket.sent, [payload, payload]);
    } finally {
        hook.restore();
    }
    assert.deepEqual(
        Object.getOwnPropertyDescriptor(ListenerFailureWebSocket.prototype, "send"),
        originalDescriptor,
    );
});

test("WebSocket 代理只捕获公开比赛场 866461 映射到的内部赛事牌谱", () => {
    const captures = [];
    const resolvedContests = [];
    const HookedWebSocket = createWebSocketProxy(
        FakeWebSocket,
        (records, request) => captures.push({ records, request }),
        () => {},
        {
            targetContestId: TARGET_CONTEST_ID,
            onContestResolved: (contest) => resolvedContests.push(contest),
        },
    );
    const socket = new HookedWebSocket("wss://example.test/gateway");

    const targetLookup = concatBytes(
        Uint8Array.of(2, 1, 0),
        wrapper(
            ".lq.Lobby.fetchCustomizedContestByContestId",
            fieldVarint(1, TARGET_CONTEST_ID),
        ),
    );
    socket.send(targetLookup);
    socket.emit("message", concatBytes(
        Uint8Array.of(3, 1, 0),
        wrapper(
            ".lq.ResFetchCustomizedContestByContestId",
            fieldBytes(2, contestInfo(TARGET_CONTEST_UNIQUE_ID, TARGET_CONTEST_ID, "Santi League")),
        ),
    ));

    const targetList = concatBytes(
        Uint8Array.of(2, 2, 0),
        wrapper(
            ".lq.Lobby.fetchCustomizedContestGameRecords",
            concatBytes(fieldVarint(1, TARGET_CONTEST_UNIQUE_ID), fieldVarint(2, 0)),
        ),
    );
    socket.send(targetList);
    socket.emit("message", concatBytes(
        Uint8Array.of(3, 2, 0),
        wrapper(".lq.ResFetchCustomizedContestGameRecords", fieldBytes(3, record({
            uuid: UUID_NEW,
            startTime: 1_777_100_000,
            endTime: 1_777_101_000,
            contestUniqueId: TARGET_CONTEST_UNIQUE_ID,
            nickname: "santi",
        }))),
    ));

    const otherUniqueId = 32_164_404;
    const otherContestId = 866_462;
    const otherLookup = concatBytes(
        Uint8Array.of(2, 3, 0),
        wrapper(
            ".lq.Lobby.fetchCustomizedContestByContestId",
            fieldVarint(1, otherContestId),
        ),
    );
    socket.send(otherLookup);
    socket.emit("message", concatBytes(
        Uint8Array.of(3, 3, 0),
        wrapper(
            ".lq.ResFetchCustomizedContestByContestId",
            fieldBytes(2, contestInfo(otherUniqueId, otherContestId, "Other League")),
        ),
    ));
    const otherList = concatBytes(
        Uint8Array.of(2, 4, 0),
        wrapper(
            ".lq.Lobby.fetchCustomizedContestGameRecords",
            concatBytes(fieldVarint(1, otherUniqueId), fieldVarint(2, 0)),
        ),
    );
    socket.send(otherList);
    socket.emit("message", concatBytes(
        Uint8Array.of(3, 4, 0),
        wrapper(".lq.ResFetchCustomizedContestGameRecords", fieldBytes(3, record({
            uuid: UUID_OLD,
            startTime: 1_777_000_000,
            endTime: 1_777_001_000,
            contestUniqueId: otherUniqueId,
            nickname: "DreamKQ",
        }))),
    ));

    const rankList = concatBytes(
        Uint8Array.of(2, 5, 0),
        wrapper(
            ".lq.Lobby.fetchGameRecordList",
            concatBytes(fieldVarint(1, 0), fieldVarint(2, 30), fieldVarint(3, 2)),
        ),
    );
    socket.send(rankList);
    socket.emit("message", concatBytes(
        Uint8Array.of(3, 5, 0),
        wrapper(".lq.ResGameRecordList", fieldBytes(3, record({
            uuid: UUID_OLD,
            startTime: 1_777_000_000,
            endTime: 1_777_001_000,
            contestUniqueId: 0,
            nickname: "Rank Player",
        }))),
    ));

    assert.deepEqual(socket.sent, [targetLookup, targetList, otherLookup, otherList, rankList]);
    assert.equal(resolvedContests.length, 2);
    assert.equal(captures.length, 1);
    assert.equal(captures[0].request.contestId, TARGET_CONTEST_ID);
    assert.equal(captures[0].request.contestUniqueId, TARGET_CONTEST_UNIQUE_ID);
    assert.equal(captures[0].records[0].contestId, TARGET_CONTEST_ID);
    assert.equal(captures[0].records[0].contestUniqueId, TARGET_CONTEST_UNIQUE_ID);
    assert.equal(captures[0].records[0].uuid, UUID_NEW);
});

test("内部赛事牌谱先返回时会等待公开比赛场映射再放行", () => {
    const captures = [];
    const HookedWebSocket = createWebSocketProxy(
        FakeWebSocket,
        (records, request) => captures.push({ records, request }),
        () => {},
        { targetContestId: TARGET_CONTEST_ID },
    );
    const socket = new HookedWebSocket("wss://example.test/gateway");

    const listFrame = concatBytes(
        Uint8Array.of(2, 10, 0),
        wrapper(
            ".lq.Lobby.fetchCustomizedContestGameRecords",
            concatBytes(fieldVarint(1, TARGET_CONTEST_UNIQUE_ID), fieldVarint(2, 0)),
        ),
    );
    socket.send(listFrame);
    socket.emit("message", concatBytes(
        Uint8Array.of(3, 10, 0),
        wrapper(".lq.ResFetchCustomizedContestGameRecords", fieldBytes(3, record({
            uuid: UUID_NEW,
            startTime: 1_777_100_000,
            endTime: 1_777_101_000,
            contestUniqueId: 0,
            nickname: "santi",
        }))),
    ));
    assert.equal(captures.length, 0);

    const lookupFrame = concatBytes(
        Uint8Array.of(2, 11, 0),
        wrapper(
            ".lq.Lobby.fetchCustomizedContestByContestId",
            fieldVarint(1, TARGET_CONTEST_ID),
        ),
    );
    socket.send(lookupFrame);
    socket.emit("message", concatBytes(
        Uint8Array.of(3, 11, 0),
        wrapper(
            ".lq.ResFetchCustomizedContestByContestId",
            fieldBytes(2, contestInfo(TARGET_CONTEST_UNIQUE_ID, TARGET_CONTEST_ID, "Santi League")),
        ),
    ));

    assert.equal(captures.length, 1);
    assert.equal(captures[0].request.contestId, TARGET_CONTEST_ID);
    assert.equal(captures[0].records[0].contestId, TARGET_CONTEST_ID);
    assert.equal(captures[0].records[0].contestUniqueId, TARGET_CONTEST_UNIQUE_ID);
});

test("缓存的公开比赛场映射可直接识别内部赛事请求", () => {
    const captures = [];
    const HookedWebSocket = createWebSocketProxy(
        FakeWebSocket,
        (records, request) => captures.push({ records, request }),
        () => {},
        {
            targetContestId: TARGET_CONTEST_ID,
            initialContestMappings: [{
                uniqueId: TARGET_CONTEST_UNIQUE_ID,
                contestId: TARGET_CONTEST_ID,
            }],
        },
    );
    const socket = new HookedWebSocket("wss://example.test/gateway");
    const listFrame = concatBytes(
        Uint8Array.of(2, 12, 0),
        wrapper(
            ".lq.Lobby.fetchCustomizedContestGameRecords",
            concatBytes(fieldVarint(1, TARGET_CONTEST_UNIQUE_ID), fieldVarint(2, 0)),
        ),
    );
    socket.send(listFrame);
    socket.emit("message", concatBytes(
        Uint8Array.of(3, 12, 0),
        wrapper(".lq.ResFetchCustomizedContestGameRecords", fieldBytes(3, record({
            uuid: UUID_NEW,
            startTime: 1_777_100_000,
            endTime: 1_777_101_000,
            contestUniqueId: TARGET_CONTEST_UNIQUE_ID,
            nickname: "santi",
        }))),
    ));

    assert.equal(socket.sent[0], listFrame);
    assert.equal(captures.length, 1);
    assert.equal(captures[0].request.contestId, TARGET_CONTEST_ID);
    assert.equal(captures[0].records[0].contestId, TARGET_CONTEST_ID);
});

test("WebSocket 代理把 V2 游标上下文传给后续翻页响应", () => {
    const captures = [];
    const HookedWebSocket = createWebSocketProxy(
        FakeWebSocket,
        (records, request) => captures.push({ records, request }),
    );
    const socket = new HookedWebSocket("wss://example.test/gateway");

    const startFrame = concatBytes(
        Uint8Array.of(2, 1, 0),
        wrapper(
            ".lq.Lobby.fetchGameRecordListV2",
            concatBytes(fieldVarint(1, 4), fieldVarint(2, 1_777_000_000), fieldVarint(3, 1_777_200_000)),
        ),
    );
    socket.send(startFrame);
    socket.emit("message", concatBytes(
        Uint8Array.of(3, 1, 0),
        wrapper(".lq.ResGameRecordListV2", fieldBytes(2, "iterator-123")),
    ));

    const nextFrame = concatBytes(
        Uint8Array.of(2, 2, 0),
        wrapper(
            ".lq.Lobby.fetchNextGameRecordList",
            concatBytes(fieldBytes(1, "iterator-123"), fieldVarint(2, 30)),
        ),
    );
    socket.send(nextFrame);
    socket.emit("message", concatBytes(
        Uint8Array.of(3, 2, 0),
        wrapper(".lq.ResNextGameRecordList", concatBytes(
            fieldVarint(2, 0),
            fieldBytes(3, recordListEntry({
                uuid: UUID_NEW,
                startTime: 1_777_100_000,
                endTime: 1_777_101_000,
                tag: 4,
                subtag: 20_808_476,
                nickname: "santi",
            })),
        )),
    ));

    assert.equal(socket.sent[0], startFrame);
    assert.equal(socket.sent[1], nextFrame);
    assert.equal(captures.length, 1);
    assert.equal(captures[0].request.kind, "v2-next");
    assert.equal(captures[0].request.tag, 4);
    assert.equal(captures[0].records[0].contestId, 0);
    assert.equal(captures[0].records[0].uuid, UUID_NEW);
});

test("按固定公开比赛场、日期和已导出集合筛选", () => {
    const records = mergeRecords([
        {
            uuid: UUID_OLD,
            endTime: 100,
            requestType: 4,
            contestId: TARGET_CONTEST_ID,
        },
        {
            uuid: UUID_NEW,
            endTime: 200,
            requestType: 4,
            contestId: 866_462,
        },
    ]);
    const result = filterRecords(records, {
        type: 4,
        contestId: TARGET_CONTEST_ID,
        fromTimestamp: 50,
        toTimestampExclusive: 300,
        onlyNew: true,
        exportedUuids: new Set([UUID_NEW]),
    });
    assert.deepEqual(result.map((item) => item.uuid), [UUID_OLD]);
});
