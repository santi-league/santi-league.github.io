// ==UserScript==
// @name         Santi League 比赛场 866461 牌谱导出器
// @namespace    santi-league
// @version      1.3.0
// @description  只收集雀魂比赛场 866461 正常加载的牌谱，并复制或下载为 links.txt
// @match        https://game.maj-soul.com/*
// @match        https://game.maj-soul.net/*
// @match        https://mahjongsoul.game.yo-star.com/*
// @match        https://game.mahjongsoul.com/*
// @match        https://majsoul.union-game.com/*
// @run-at       document-start
// @noframes
// @grant        unsafeWindow
// @grant        GM_registerMenuCommand
// @grant        GM_setClipboard
// ==/UserScript==

(function (root) {
    "use strict";

    const OUTPUT_BASE_URL = "https://game.maj-soul.com/1/";
    const OUTPUT_PREFIX = "雀魂牌譜:";
    const TARGET_CONTEST_ID = 866_461;
    const TARGET_CONTEST_UNIQUE_ID = 20_808_476;
    const HISTORY_KEY = `santi-paipu-exported-contest-${TARGET_CONTEST_ID}-v1`;
    const LEGACY_HISTORY_KEY = "santi-paipu-exported-v1";
    const CONTEST_MAPPING_KEY = `santi-paipu-contest-${TARGET_CONTEST_ID}-mapping-v1`;
    const MAX_HISTORY_SIZE = 5000;
    const UUID_SOURCE = "\\d{6}-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}";
    const UUID_PATTERN = new RegExp(`^${UUID_SOURCE}$`, "i");
    const UUID_GLOBAL_PATTERN = new RegExp(UUID_SOURCE, "gi");
    const IDS = {
        button: "santi-paipu-export-button",
        overlay: "santi-paipu-export-overlay",
        dialog: "santi-paipu-export-dialog",
        status: "santi-paipu-export-status",
        rows: "santi-paipu-export-rows",
        summary: "santi-paipu-export-summary",
    };

    function getField(value, ...names) {
        if (!value || typeof value !== "object") {
            return undefined;
        }
        for (const name of names) {
            if (Object.prototype.hasOwnProperty.call(value, name)) {
                return value[name];
            }
        }
        return undefined;
    }

    function toUint8Array(data) {
        if (!data) {
            return null;
        }
        if (data instanceof Uint8Array) {
            return new Uint8Array(data.buffer, data.byteOffset, data.byteLength);
        }
        if (typeof ArrayBuffer !== "undefined" && data instanceof ArrayBuffer) {
            return new Uint8Array(data);
        }
        if (typeof ArrayBuffer !== "undefined" && ArrayBuffer.isView(data)) {
            return new Uint8Array(data.buffer, data.byteOffset, data.byteLength);
        }
        if (Object.prototype.toString.call(data) === "[object ArrayBuffer]") {
            return new Uint8Array(data);
        }
        return null;
    }

    function readVarint(bytes, state) {
        let result = 0n;
        let shift = 0n;
        while (state.offset < bytes.length && shift <= 70n) {
            const byte = bytes[state.offset++];
            result |= BigInt(byte & 0x7f) << shift;
            if ((byte & 0x80) === 0) {
                return result <= BigInt(Number.MAX_SAFE_INTEGER) ? Number(result) : result;
            }
            shift += 7n;
        }
        throw new Error("截断的 protobuf varint");
    }

    function decodeProtoFields(input) {
        const bytes = toUint8Array(input);
        if (!bytes) {
            throw new TypeError("protobuf 输入必须是二进制数据");
        }

        const fields = new Map();
        const state = { offset: 0 };
        const push = (number, value) => {
            if (!fields.has(number)) {
                fields.set(number, []);
            }
            fields.get(number).push(value);
        };

        while (state.offset < bytes.length) {
            const tag = Number(readVarint(bytes, state));
            const fieldNumber = tag >>> 3;
            const wireType = tag & 7;
            if (!fieldNumber) {
                throw new Error("无效的 protobuf 字段编号");
            }

            if (wireType === 0) {
                push(fieldNumber, readVarint(bytes, state));
            } else if (wireType === 1) {
                if (state.offset + 8 > bytes.length) {
                    throw new Error("截断的 protobuf fixed64");
                }
                push(fieldNumber, bytes.subarray(state.offset, state.offset + 8));
                state.offset += 8;
            } else if (wireType === 2) {
                const length = Number(readVarint(bytes, state));
                if (!Number.isSafeInteger(length) || length < 0 || state.offset + length > bytes.length) {
                    throw new Error("截断的 protobuf length-delimited 字段");
                }
                push(fieldNumber, bytes.subarray(state.offset, state.offset + length));
                state.offset += length;
            } else if (wireType === 5) {
                if (state.offset + 4 > bytes.length) {
                    throw new Error("截断的 protobuf fixed32");
                }
                push(fieldNumber, bytes.subarray(state.offset, state.offset + 4));
                state.offset += 4;
            } else {
                throw new Error(`不支持的 protobuf wire type：${wireType}`);
            }
        }
        return fields;
    }

    function firstField(fields, number, fallback = undefined) {
        const values = fields.get(number);
        return values && values.length ? values[0] : fallback;
    }

    function decodeText(bytes) {
        if (!bytes) {
            return "";
        }
        if (typeof TextDecoder !== "undefined") {
            return new TextDecoder("utf-8").decode(bytes);
        }
        let text = "";
        for (let index = 0; index < bytes.length; index += 1) {
            text += String.fromCharCode(bytes[index]);
        }
        return text;
    }

    function decodeEnvelope(input) {
        const fields = decodeProtoFields(input);
        return {
            name: decodeText(firstField(fields, 1)),
            data: firstField(fields, 2, new Uint8Array()),
        };
    }

    function extractUuidsFromBytes(input) {
        const bytes = toUint8Array(input);
        if (!bytes) {
            return [];
        }
        const text = decodeText(bytes);
        const matches = text.match(UUID_GLOBAL_PATTERN) || [];
        return Array.from(new Set(matches.map((uuid) => uuid.toLowerCase())));
    }

    function decodeAccount(input) {
        const fields = decodeProtoFields(input);
        return {
            accountId: Number(firstField(fields, 1, 0)) || 0,
            seat: Number(firstField(fields, 2, 0)) || 0,
            nickname: decodeText(firstField(fields, 3)) || "未知玩家",
        };
    }

    function decodeRecordPlayerResult(input) {
        const fields = decodeProtoFields(input);
        return {
            accountId: Number(firstField(fields, 2, 0)) || 0,
            seat: Number(firstField(fields, 6, 0)) || 0,
            nickname: decodeText(firstField(fields, 3)) || "未知玩家",
        };
    }

    function decodeRecordGame(input, requestType = 0) {
        const fields = decodeProtoFields(input);
        const uuid = decodeText(firstField(fields, 1)).toLowerCase();
        if (!UUID_PATTERN.test(uuid)) {
            return null;
        }

        let category = 0;
        let roomId = 0;
        let contestUniqueId = 0;
        const configBytes = firstField(fields, 5);
        if (configBytes) {
            const config = decodeProtoFields(configBytes);
            category = Number(firstField(config, 1, 0)) || 0;
            const metaBytes = firstField(config, 3);
            if (metaBytes) {
                const meta = decodeProtoFields(metaBytes);
                roomId = Number(firstField(meta, 1, 0)) || 0;
                contestUniqueId = Number(firstField(meta, 3, 0)) || 0;
            }
        }

        const accountBytes = fields.get(11) || [];
        const accounts = accountBytes.map(decodeAccount).sort((a, b) => a.seat - b.seat);
        return {
            uuid,
            startTime: Number(firstField(fields, 2, 0)) || 0,
            endTime: Number(firstField(fields, 3, 0)) || 0,
            requestType: Number(requestType) || 0,
            category,
            roomId,
            contestId: 0,
            contestUniqueId,
            accounts,
        };
    }

    function includeMissingFallbackRecords(records, fallbackRecords) {
        const seen = new Set(records.map((record) => record.uuid));
        return records.concat(fallbackRecords.filter((record) => !seen.has(record.uuid)));
    }

    function decodeGameRecordListResponse(wrapperBytes, requestType = 0) {
        const envelope = decodeEnvelope(wrapperBytes);
        const response = decodeProtoFields(envelope.data);
        const records = (response.get(3) || [])
            .map((bytes) => {
                try {
                    return decodeRecordGame(bytes, requestType);
                } catch (_) {
                    return null;
                }
            })
            .filter(Boolean);

        // Schema changes should not make the exporter completely unusable. The
        // UUID is an ASCII protobuf string, so preserve any entry whose richer
        // metadata failed to decode without replacing successfully parsed data.
        const fallbackRecords = extractUuidsFromBytes(wrapperBytes).map((uuid) => ({
            uuid,
            startTime: timestampFromUuid(uuid),
            endTime: timestampFromUuid(uuid),
            requestType: Number(requestType) || 0,
            category: 0,
            roomId: 0,
            contestId: 0,
            contestUniqueId: 0,
            accounts: [],
        }));
        return includeMissingFallbackRecords(records, fallbackRecords);
    }

    function recordTypeFromV2Tag(tag) {
        const value = Number(tag) || 0;
        // V2 uses ALL=0, RANK=1, FRIEND=2, ACTIVITY=3, MATCH=4,
        // COLLECT=5. Normalize it to the legacy/exporter convention where
        // FRIEND=1, RANK=2 and customized matches=4.
        if (value === 1) {
            return 2;
        }
        if (value === 2) {
            return 1;
        }
        return value;
    }

    function decodeRecordListEntry(input, requestTag = 0) {
        const fields = decodeProtoFields(input);
        const uuid = decodeText(firstField(fields, 2)).toLowerCase();
        if (!UUID_PATTERN.test(uuid)) {
            return null;
        }

        const tag = Number(firstField(fields, 5, 0)) || Number(requestTag) || 0;
        const recordType = recordTypeFromV2Tag(tag);
        const playerBytes = fields.get(7) || [];
        return {
            uuid,
            startTime: Number(firstField(fields, 3, 0)) || timestampFromUuid(uuid),
            endTime: Number(firstField(fields, 4, 0)) || timestampFromUuid(uuid),
            requestType: recordType,
            category: recordType,
            // V2 subtag describes a match configuration or game mode; it is
            // not a room/contest id. Exact contest ids come from RecordGame or
            // fetchCustomizedContestGameRecords request context instead.
            roomId: 0,
            contestId: 0,
            contestUniqueId: 0,
            accounts: playerBytes.map(decodeRecordPlayerResult).sort((a, b) => a.seat - b.seat),
        };
    }

    function fallbackRecordListEntries(wrapperBytes, requestTag = 0) {
        const recordType = recordTypeFromV2Tag(requestTag);
        return extractUuidsFromBytes(wrapperBytes).map((uuid) => ({
            uuid,
            startTime: timestampFromUuid(uuid),
            endTime: timestampFromUuid(uuid),
            requestType: recordType,
            category: recordType,
            roomId: 0,
            contestId: 0,
            contestUniqueId: 0,
            accounts: [],
        }));
    }

    function decodeGameRecordListV2Response(wrapperBytes) {
        const envelope = decodeEnvelope(wrapperBytes);
        const response = decodeProtoFields(envelope.data);
        return {
            iterator: decodeText(firstField(response, 2)),
            iteratorExpire: Number(firstField(response, 3, 0)) || 0,
            actualBeginTime: Number(firstField(response, 4, 0)) || 0,
            actualEndTime: Number(firstField(response, 5, 0)) || 0,
        };
    }

    function decodeNextGameRecordListResponse(wrapperBytes, requestTag = 0) {
        const envelope = decodeEnvelope(wrapperBytes);
        const response = decodeProtoFields(envelope.data);
        const records = (response.get(3) || [])
            .map((bytes) => {
                try {
                    return decodeRecordListEntry(bytes, requestTag);
                } catch (_) {
                    return null;
                }
            })
            .filter(Boolean);
        return {
            hasNext: Boolean(Number(firstField(response, 2, 0))),
            iteratorExpire: Number(firstField(response, 4, 0)) || 0,
            nextEndTime: Number(firstField(response, 5, 0)) || 0,
            records: includeMissingFallbackRecords(
                records,
                fallbackRecordListEntries(wrapperBytes, requestTag),
            ),
        };
    }

    function decodeGameRecordsDetailV2Response(wrapperBytes, requestTag = 0) {
        const envelope = decodeEnvelope(wrapperBytes);
        const response = decodeProtoFields(envelope.data);
        const records = (response.get(2) || [])
            .map((bytes) => {
                try {
                    return decodeRecordListEntry(bytes, requestTag);
                } catch (_) {
                    return null;
                }
            })
            .filter(Boolean);
        return includeMissingFallbackRecords(records, fallbackRecordListEntries(wrapperBytes, requestTag));
    }

    function decodeCustomizedContestLookupResponse(wrapperBytes) {
        const envelope = decodeEnvelope(wrapperBytes);
        const response = decodeProtoFields(envelope.data);
        const contestInfoBytes = firstField(response, 2);
        if (!contestInfoBytes) {
            return null;
        }
        const contestInfo = decodeProtoFields(contestInfoBytes);
        const uniqueId = Number(firstField(contestInfo, 1, 0)) || 0;
        const contestId = Number(firstField(contestInfo, 2, 0)) || 0;
        if (!uniqueId || !contestId) {
            return null;
        }
        return {
            uniqueId,
            contestId,
            contestName: decodeText(firstField(contestInfo, 3)),
        };
    }

    function decodeRecordListRequest(wrapperBytes) {
        const envelope = decodeEnvelope(wrapperBytes);
        const request = decodeProtoFields(envelope.data);
        if (/fetchCustomizedContestByContestId$/i.test(envelope.name)) {
            return {
                kind: "contest-lookup",
                method: envelope.name,
                contestId: Number(firstField(request, 1, 0)) || 0,
            };
        }
        if (/fetchGameRecordListV2$/i.test(envelope.name)) {
            const tag = Number(firstField(request, 1, 0)) || 0;
            return {
                kind: "v2-start",
                method: envelope.name,
                tag,
                type: recordTypeFromV2Tag(tag),
                beginTime: Number(firstField(request, 2, 0)) || 0,
                endTime: Number(firstField(request, 3, 0)) || 0,
            };
        }
        if (/fetchNextGameRecordList$/i.test(envelope.name)) {
            return {
                kind: "v2-next",
                method: envelope.name,
                iterator: decodeText(firstField(request, 1)),
                count: Number(firstField(request, 2, 0)) || 0,
            };
        }
        if (/fetchGameRecordsDetailV2$/i.test(envelope.name)) {
            return {
                kind: "v2-detail",
                method: envelope.name,
            };
        }
        if (/fetchCustomizedContestGameRecords$/i.test(envelope.name)) {
            return {
                kind: "contest-list",
                method: envelope.name,
                contestUniqueId: Number(firstField(request, 1, 0)) || 0,
                lastIndex: Number(firstField(request, 2, 0)) || 0,
                type: 4,
            };
        }
        if (/fetchGameRecordList$/i.test(envelope.name)) {
            return {
                kind: "v1-list",
                method: envelope.name,
                start: Number(firstField(request, 1, 0)) || 0,
                count: Number(firstField(request, 2, 0)) || 0,
                type: Number(firstField(request, 3, 0)) || 0,
            };
        }
        return null;
    }

    function timestampFromUuid(uuid) {
        const match = String(uuid || "").match(/^(\d{2})(\d{2})(\d{2})-/);
        if (!match) {
            return 0;
        }
        const date = new Date(2000 + Number(match[1]), Number(match[2]) - 1, Number(match[3]), 12, 0, 0);
        return Number.isNaN(date.getTime()) ? 0 : Math.floor(date.getTime() / 1000);
    }

    function normalizeAccount(account) {
        return {
            accountId: Number(getField(account, "accountId", "account_id")) || 0,
            seat: Number(getField(account, "seat")) || 0,
            nickname: String(getField(account, "nickname") || "未知玩家"),
        };
    }

    function normalizeRecord(record, fallbackType = 0) {
        const uuid = String(getField(record, "uuid", "game_uuid", "gameUuid") || "").trim().toLowerCase();
        if (!UUID_PATTERN.test(uuid)) {
            return null;
        }
        const config = getField(record, "config") || {};
        const meta = getField(config, "meta") || {};
        const rawPlayers = getField(record, "players");
        let rawAccounts = getField(record, "accounts", "account_list", "accountList");
        if (!Array.isArray(rawAccounts) && Array.isArray(rawPlayers)) {
            rawAccounts = rawPlayers;
        }
        const rawTag = getField(record, "tag");
        const isV2Entry = rawTag !== undefined
            && (Array.isArray(rawPlayers)
                || getField(record, "version", "standardRule", "standard_rule") !== undefined);
        const v2Type = isV2Entry ? recordTypeFromV2Tag(rawTag) : 0;
        return {
            uuid,
            startTime: Number(getField(record, "startTime", "start_time")) || timestampFromUuid(uuid),
            endTime: Number(getField(record, "endTime", "end_time")) || timestampFromUuid(uuid),
            requestType: Number(getField(record, "requestType")) || v2Type || Number(fallbackType) || 0,
            category: Number(getField(record, "category")) || v2Type || Number(getField(config, "category")) || 0,
            roomId: Number(getField(record, "roomId"))
                || (isV2Entry ? 0 : Number(getField(meta, "room_id", "roomId")))
                || 0,
            // contestId is the public six-digit value entered in the lobby.
            // contestUniqueId is the internal value stored in GameMetaData.
            contestId: Number(getField(record, "contestId", "contest_id")) || 0,
            contestUniqueId: Number(getField(
                record,
                "contestUniqueId",
                "contest_unique_id",
                "contestUid",
                "contest_uid",
            ))
                || (isV2Entry ? 0 : Number(getField(meta, "contest_uid", "contestUid")))
                || 0,
            accounts: Array.isArray(rawAccounts)
                ? rawAccounts.map(normalizeAccount).sort((a, b) => a.seat - b.seat)
                : [],
        };
    }

    function mergeRecords(records) {
        const byUuid = new Map();
        for (const input of Array.isArray(records) ? records : []) {
            const record = normalizeRecord(input);
            if (!record) {
                continue;
            }
            const previous = byUuid.get(record.uuid);
            if (!previous) {
                byUuid.set(record.uuid, record);
                continue;
            }
            byUuid.set(record.uuid, {
                ...previous,
                ...record,
                startTime: record.startTime || previous.startTime,
                endTime: record.endTime || previous.endTime,
                requestType: record.requestType || previous.requestType,
                category: record.category || previous.category,
                roomId: record.roomId || previous.roomId,
                contestId: record.contestId || previous.contestId,
                contestUniqueId: record.contestUniqueId || previous.contestUniqueId,
                accounts: record.accounts.length ? record.accounts : previous.accounts,
            });
        }
        return Array.from(byUuid.values()).sort((a, b) => b.endTime - a.endTime || a.uuid.localeCompare(b.uuid));
    }

    function isRecordType(record, type) {
        if (!type) {
            return true;
        }
        if (type === 4) {
            return record.contestId > 0
                || record.contestUniqueId > 0
                || record.requestType === 4
                || record.category === 4;
        }
        if (type === 1) {
            return record.roomId > 0 || record.requestType === 1 || record.category === 1;
        }
        return record.requestType === type || record.category === type;
    }

    function filterRecords(records, options = {}) {
        const fromTimestamp = Number(options.fromTimestamp) || 0;
        const toTimestampExclusive = Number(options.toTimestampExclusive) || Number.POSITIVE_INFINITY;
        const type = Number(options.type) || 0;
        const contestId = Number(options.contestId) || 0;
        const contestUniqueId = Number(options.contestUniqueId) || 0;
        const exportedUuids = options.exportedUuids instanceof Set ? options.exportedUuids : new Set();
        return mergeRecords(records).filter((record) => {
            const timestamp = record.endTime || record.startTime;
            return timestamp >= fromTimestamp
                && timestamp < toTimestampExclusive
                && isRecordType(record, type)
                && (!contestId || record.contestId === contestId)
                && (!contestUniqueId || record.contestUniqueId === contestUniqueId)
                && (!options.onlyNew || !exportedUuids.has(record.uuid));
        });
    }

    function buildPaipuUrl(uuid, baseUrl = OUTPUT_BASE_URL) {
        if (!UUID_PATTERN.test(String(uuid || ""))) {
            throw new Error(`无效的牌谱 UUID：${uuid || "(空)"}`);
        }
        const url = new URL(baseUrl);
        // The optional `_a...` value is an encoded perspective id, not a raw
        // account id. It is unnecessary for downloading, so deliberately omit it.
        url.searchParams.set("paipu", String(uuid).toLowerCase());
        return url.toString();
    }

    function serializeLinks(records, baseUrl = OUTPUT_BASE_URL) {
        const normalized = mergeRecords(records);
        if (!normalized.length) {
            return "";
        }
        return `${normalized.map((record) => `${OUTPUT_PREFIX}${buildPaipuUrl(record.uuid, baseUrl)}`).join("\n")}\n`;
    }

    function createWebSocketObserver(onRecords, onError = () => {}, options = {}) {
        const targetContestId = Number(options.targetContestId) || 0;
        const onContestResolved = typeof options.onContestResolved === "function"
            ? options.onContestResolved
            : () => {};
        const reportError = (error) => {
            try {
                onError(error);
            } catch (_) {
                // Diagnostics must never interfere with the game's network traffic.
            }
        };
        // The public contest_id (866461) and the internal unique_id used by
        // the record-list request are different values. Learn their mapping
        // from the page's normal lookup response; do not send a lookup ourselves.
        const contestIdsByUniqueId = new Map();
        for (const mapping of Array.isArray(options.initialContestMappings)
            ? options.initialContestMappings
            : []) {
            const uniqueId = Number(mapping?.uniqueId) || 0;
            const contestId = Number(mapping?.contestId) || 0;
            if (Number.isSafeInteger(uniqueId) && uniqueId > 0
                && Number.isSafeInteger(contestId) && contestId > 0) {
                contestIdsByUniqueId.set(uniqueId, contestId);
            }
        }

        // If a cached page sends the internal record request before repeating
        // the public-id lookup, keep a small in-memory buffer. A later normal
        // lookup response either releases the target records or discards them.
        const MAX_DEFERRED_RECORDS = 500;
        const deferredByUniqueId = new Map();
        let deferredRecordCount = 0;

        const annotateContestIds = (records) => records.map((record) => {
            const contestId = record.contestId
                || contestIdsByUniqueId.get(record.contestUniqueId)
                || 0;
            return contestId === record.contestId ? record : { ...record, contestId };
        });

        const emitOrDeferRecords = (records, request) => {
            const annotated = annotateContestIds(records);
            if (!targetContestId) {
                if (annotated.length) {
                    onRecords(annotated, request);
                }
                return;
            }

            const ready = [];
            const unresolved = new Map();
            for (const record of annotated) {
                if (record.contestId === targetContestId) {
                    ready.push(record);
                } else if (!record.contestId && record.contestUniqueId > 0) {
                    if (!unresolved.has(record.contestUniqueId)) {
                        unresolved.set(record.contestUniqueId, []);
                    }
                    unresolved.get(record.contestUniqueId).push(record);
                }
            }

            for (const [uniqueId, unresolvedRecords] of unresolved) {
                const remaining = MAX_DEFERRED_RECORDS - deferredRecordCount;
                if (remaining <= 0) {
                    break;
                }
                const buffered = unresolvedRecords.slice(0, remaining);
                if (!deferredByUniqueId.has(uniqueId)) {
                    deferredByUniqueId.set(uniqueId, []);
                }
                deferredByUniqueId.get(uniqueId).push({ records: buffered, request });
                deferredRecordCount += buffered.length;
            }

            if (ready.length) {
                onRecords(ready, request);
            }
        };

        const resolveContest = (contest) => {
            contestIdsByUniqueId.set(contest.uniqueId, contest.contestId);
            const deferred = deferredByUniqueId.get(contest.uniqueId) || [];
            deferredByUniqueId.delete(contest.uniqueId);
            deferredRecordCount -= deferred.reduce((sum, batch) => sum + batch.records.length, 0);
            if (!targetContestId || contest.contestId === targetContestId) {
                for (const batch of deferred) {
                    onRecords(
                        batch.records.map((record) => ({ ...record, contestId: contest.contestId })),
                        { ...batch.request, contestId: contest.contestId },
                    );
                }
            }
            onContestResolved(contest);
        };

        const socketStates = new WeakMap();
        const ensureSocket = (socket) => {
            let state = socketStates.get(socket);
            if (!state) {
                state = {
                    listenerAttached: false,
                    pending: new Map(),
                    iteratorContexts: new Map(),
                };
                socketStates.set(socket, state);
            }
            if (state.listenerAttached) {
                return state;
            }
            try {
                const handleResponse = (data) => {
                    const bytes = toUint8Array(data);
                    if (!bytes || bytes.length < 4 || bytes[0] !== 3) {
                        return;
                    }
                    const index = bytes[1] | (bytes[2] << 8);
                    const request = state.pending.get(index);
                    if (!request) {
                        return;
                    }
                    state.pending.delete(index);
                    try {
                        let records = [];
                        if (request.kind === "contest-lookup") {
                            const contest = decodeCustomizedContestLookupResponse(bytes.subarray(3));
                            if (contest && contest.contestId === request.contestId) {
                                resolveContest(contest);
                            }
                            return;
                        }
                        if (request.kind === "v2-start") {
                            const response = decodeGameRecordListV2Response(bytes.subarray(3));
                            if (response.iterator) {
                                state.iteratorContexts.set(response.iterator, request);
                            }
                            return;
                        }
                        if (request.kind === "v2-next") {
                            const response = decodeNextGameRecordListResponse(
                                bytes.subarray(3),
                                request.tag || request.type,
                            );
                            records = response.records;
                            if (!response.hasNext && request.iterator) {
                                state.iteratorContexts.delete(request.iterator);
                            }
                        } else if (request.kind === "v2-detail") {
                            records = decodeGameRecordsDetailV2Response(bytes.subarray(3), request.tag || request.type);
                        } else {
                            records = decodeGameRecordListResponse(bytes.subarray(3), request.type);
                            if (request.kind === "contest-list") {
                                records = records.map((record) => ({
                                    ...record,
                                    requestType: 4,
                                    category: record.category || 4,
                                    contestId: request.contestId || 0,
                                    contestUniqueId: record.contestUniqueId || request.contestUniqueId,
                                }));
                            }
                        }
                        emitOrDeferRecords(records, request);
                    } catch (error) {
                        reportError(error);
                    }
                };
                socket.addEventListener("message", (event) => {
                    const bytes = toUint8Array(event.data);
                    if (bytes) {
                        handleResponse(bytes);
                    } else if (event.data && typeof event.data.arrayBuffer === "function") {
                        event.data.arrayBuffer()
                            .then((buffer) => handleResponse(new Uint8Array(buffer)))
                            .catch(reportError);
                    }
                });
                state.listenerAttached = true;
            } catch (error) {
                reportError(error);
            }
            return state;
        };

        const observeSend = (socket, data) => {
            try {
                const state = ensureSocket(socket);
                const bytes = toUint8Array(data);
                if (!bytes || bytes.length < 4 || bytes[0] !== 2) {
                    return;
                }
                const request = decodeRecordListRequest(bytes.subarray(3));
                if (!request) {
                    return;
                }
                const index = bytes[1] | (bytes[2] << 8);
                const context = request.kind === "v2-next"
                    ? state.iteratorContexts.get(request.iterator)
                    : null;
                const contestId = request.kind === "contest-list"
                    ? contestIdsByUniqueId.get(request.contestUniqueId) || 0
                    : 0;
                const trackedRequest = contestId ? { ...request, contestId } : request;
                state.pending.set(index, context ? { ...context, ...trackedRequest } : trackedRequest);
            } catch (error) {
                // Never interfere with the game's own WebSocket traffic.
                reportError(error);
            }
        };

        return { ensureSocket, observeSend };
    }

    function createWebSocketProxy(OriginalWebSocket, onRecords, onError = () => {}, options = {}) {
        if (typeof OriginalWebSocket !== "function") {
            throw new TypeError("WebSocket 构造器不可用");
        }
        const observer = createWebSocketObserver(onRecords, onError, options);
        return new Proxy(OriginalWebSocket, {
            construct(target, argumentsList, newTarget) {
                const socket = Reflect.construct(target, argumentsList, newTarget);
                const originalSend = socket.send.bind(socket);
                observer.ensureSocket(socket);
                socket.send = function (data) {
                    observer.observeSend(socket, data);
                    return originalSend(data);
                };
                return socket;
            },
        });
    }

    function hookWebSocketPrototype(OriginalWebSocket, onRecords, onError = () => {}, options = {}) {
        if (typeof OriginalWebSocket !== "function" || !OriginalWebSocket.prototype) {
            throw new TypeError("WebSocket 构造器不可用");
        }
        const prototype = OriginalWebSocket.prototype;
        const descriptor = Object.getOwnPropertyDescriptor(prototype, "send");
        const originalSend = prototype.send;
        if (typeof originalSend !== "function") {
            throw new TypeError("WebSocket.send 不可用");
        }
        const observer = createWebSocketObserver(onRecords, onError, options);
        const wrappedSend = function (data) {
            observer.observeSend(this, data);
            return Reflect.apply(originalSend, this, arguments);
        };
        Object.defineProperty(prototype, "send", {
            configurable: descriptor ? descriptor.configurable : true,
            enumerable: descriptor ? descriptor.enumerable : false,
            writable: descriptor ? descriptor.writable : true,
            value: wrappedSend,
        });
        return {
            send: wrappedSend,
            restore() {
                if (prototype.send !== wrappedSend) {
                    return;
                }
                if (descriptor) {
                    Object.defineProperty(prototype, "send", descriptor);
                } else {
                    delete prototype.send;
                }
            },
        };
    }

    if (typeof module !== "undefined" && module.exports) {
        module.exports = {
            OUTPUT_BASE_URL,
            OUTPUT_PREFIX,
            TARGET_CONTEST_ID,
            TARGET_CONTEST_UNIQUE_ID,
            UUID_PATTERN,
            buildPaipuUrl,
            createWebSocketProxy,
            decodeCustomizedContestLookupResponse,
            decodeEnvelope,
            decodeGameRecordListResponse,
            decodeGameRecordListV2Response,
            decodeGameRecordsDetailV2Response,
            decodeNextGameRecordListResponse,
            decodeProtoFields,
            decodeRecordListEntry,
            decodeRecordListRequest,
            extractUuidsFromBytes,
            filterRecords,
            hookWebSocketPrototype,
            mergeRecords,
            normalizeRecord,
            recordTypeFromV2Tag,
            serializeLinks,
            timestampFromUuid,
            toUint8Array,
        };
    }

    if (!root || !root.document) {
        return;
    }

    function isPositiveUint32(value) {
        return Number.isInteger(value) && value > 0 && value <= 0xffff_ffff;
    }

    function loadTargetContestUniqueId() {
        try {
            const mapping = JSON.parse(root.localStorage.getItem(CONTEST_MAPPING_KEY) || "null");
            const contestId = Number(mapping?.contestId) || 0;
            const uniqueId = Number(mapping?.uniqueId) || 0;
            return contestId === TARGET_CONTEST_ID && isPositiveUint32(uniqueId) ? uniqueId : 0;
        } catch (_) {
            return 0;
        }
    }

    function saveTargetContestMapping(contest) {
        try {
            if (contest.contestId === TARGET_CONTEST_ID && isPositiveUint32(contest.uniqueId)) {
                root.localStorage.setItem(CONTEST_MAPPING_KEY, JSON.stringify({
                    contestId: contest.contestId,
                    uniqueId: contest.uniqueId,
                }));
            }
        } catch (_) {
            // The in-memory mapping is enough for the current page session.
        }
    }

    const pageWindow = typeof unsafeWindow !== "undefined" && unsafeWindow ? unsafeWindow : root;
    const capturedByUuid = new Map();
    let visibleRecords = [];
    let lastCaptureAt = 0;
    let hookedWebSocketSend = null;
    let targetContestUniqueId = TARGET_CONTEST_UNIQUE_ID;

    function addCapturedRecords(records, refreshDialog = true) {
        let changed = false;
        for (const record of mergeRecords(records)) {
            const previous = capturedByUuid.get(record.uuid);
            let merged = previous ? mergeRecords([previous, record])[0] : record;
            const belongsToTarget = merged.contestId === TARGET_CONTEST_ID
                || (targetContestUniqueId > 0 && merged.contestUniqueId === targetContestUniqueId);
            if (!belongsToTarget) {
                continue;
            }
            if (!merged.contestId) {
                merged = { ...merged, contestId: TARGET_CONTEST_ID };
            }
            if (!previous
                || merged.startTime !== previous.startTime
                || merged.endTime !== previous.endTime
                || merged.requestType !== previous.requestType
                || merged.category !== previous.category
                || merged.roomId !== previous.roomId
                || merged.contestId !== previous.contestId
                || merged.contestUniqueId !== previous.contestUniqueId
                || merged.accounts.length !== previous.accounts.length) {
                changed = true;
            }
            capturedByUuid.set(record.uuid, merged);
        }
        if (changed) {
            lastCaptureAt = Date.now();
            updateButtonLabel();
            if (refreshDialog && root.document.getElementById(IDS.dialog)) {
                refreshVisibleRecords();
            }
        }
    }

    function collectLegacyRecordMap() {
        const recordMap = pageWindow.uiscript?.UI_PaiPu?.record_map;
        if (!recordMap || typeof recordMap !== "object") {
            return;
        }
        // refreshVisibleRecords() calls this helper itself, so suppress the
        // callback into refreshVisibleRecords() to avoid a recursion loop.
        addCapturedRecords(Object.values(recordMap), false);
    }

    function installWebSocketHook() {
        const WebSocketConstructor = pageWindow.WebSocket;
        const prototype = WebSocketConstructor?.prototype;
        if (!prototype || typeof prototype.send !== "function") {
            return false;
        }
        if (hookedWebSocketSend && prototype.send === hookedWebSocketSend) {
            return true;
        }
        const existingHook = pageWindow.__santiPaipuExporterHookedSend;
        if (typeof existingHook === "function" && prototype.send === existingHook) {
            hookedWebSocketSend = existingHook;
            return true;
        }
        try {
            const hook = hookWebSocketPrototype(
                WebSocketConstructor,
                (records) => addCapturedRecords(records),
                (error) => console.warn("[santi-paipu-export] 无法解析牌谱列表响应", error),
                {
                    targetContestId: TARGET_CONTEST_ID,
                    initialContestMappings: [{
                        uniqueId: TARGET_CONTEST_UNIQUE_ID,
                        contestId: TARGET_CONTEST_ID,
                    }],
                    onContestResolved(contest) {
                        if (contest.contestId !== TARGET_CONTEST_ID) {
                            return;
                        }
                        targetContestUniqueId = contest.uniqueId;
                        saveTargetContestMapping(contest);
                        collectLegacyRecordMap();
                        if (root.document.getElementById(IDS.dialog)) {
                            refreshVisibleRecords();
                        }
                    },
                },
            );
            hookedWebSocketSend = hook.send;
            try {
                Object.defineProperty(pageWindow, "__santiPaipuExporterHookedSend", {
                    value: hook.send,
                    writable: true,
                    configurable: true,
                    enumerable: false,
                });
            } catch (_) {
                // The local reference still prevents this script from wrapping twice.
            }
            return true;
        } catch (error) {
            console.warn("[santi-paipu-export] 无法安装 WebSocket 监听器", error);
            return false;
        }
    }

    function loadExportedUuids() {
        const history = new Set();
        for (const key of [LEGACY_HISTORY_KEY, HISTORY_KEY]) {
            try {
                const parsed = JSON.parse(root.localStorage.getItem(key) || "[]");
                for (const uuid of Array.isArray(parsed) ? parsed : []) {
                    if (UUID_PATTERN.test(uuid)) {
                        history.add(uuid);
                    }
                }
            } catch (_) {
                // One malformed/blocked key should not hide the other history.
            }
        }
        return history;
    }

    function markExported(records) {
        try {
            const history = loadExportedUuids();
            for (const record of records) {
                history.add(record.uuid);
            }
            root.localStorage.setItem(HISTORY_KEY, JSON.stringify(Array.from(history).slice(-MAX_HISTORY_SIZE)));
        } catch (_) {
            // Export itself succeeded; unavailable storage should not turn it into a failure.
        }
    }

    function localDateToTimestamp(dateText, addOneDay = false) {
        if (!dateText) {
            return addOneDay ? Number.POSITIVE_INFINITY : 0;
        }
        const date = new Date(`${dateText}T00:00:00`);
        if (Number.isNaN(date.getTime())) {
            throw new Error(`日期格式无效：${dateText}`);
        }
        if (addOneDay) {
            date.setDate(date.getDate() + 1);
        }
        return Math.floor(date.getTime() / 1000);
    }

    function dateInputValue(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, "0");
        const day = String(date.getDate()).padStart(2, "0");
        return `${year}-${month}-${day}`;
    }

    function formatRecordTime(timestamp) {
        if (!timestamp) {
            return "时间未知";
        }
        return new Date(timestamp * 1000).toLocaleString(undefined, {
            year: "numeric",
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
        });
    }

    function describeRoom(record) {
        if (record.contestId) {
            return `比赛场 #${record.contestId}`;
        }
        if (record.contestUniqueId) {
            return "大会战";
        }
        if (record.roomId) {
            return "友人战";
        }
        if (record.requestType === 4 || record.category === 4) {
            return "大会战";
        }
        if (record.requestType === 2 || record.category === 2) {
            return "段位战";
        }
        if (record.requestType === 1 || record.category === 1) {
            return "友人战";
        }
        return "类型未知";
    }

    function setStatus(message, kind = "info") {
        const status = root.document.getElementById(IDS.status);
        if (status) {
            status.textContent = message;
            status.dataset.kind = kind;
        }
    }

    function updateButtonLabel() {
        const button = root.document.getElementById(IDS.button);
        if (button) {
            const count = capturedByUuid.size;
            button.textContent = count
                ? `导出 ${TARGET_CONTEST_ID} 牌谱 (${count})`
                : `导出 ${TARGET_CONTEST_ID} 牌谱`;
        }
    }

    function updateSelectionSummary() {
        const checkboxes = Array.from(root.document.querySelectorAll(`#${IDS.rows} input[type="checkbox"]`));
        const selected = checkboxes.filter((checkbox) => checkbox.checked).length;
        const summary = root.document.getElementById(IDS.summary);
        if (summary) {
            summary.textContent = `已选择 ${selected} / ${checkboxes.length} 条牌谱`;
        }
    }

    function renderRecords(records) {
        const rows = root.document.getElementById(IDS.rows);
        if (!rows) {
            return;
        }
        rows.replaceChildren();

        if (!records.length) {
            const empty = root.document.createElement("div");
            empty.className = "santi-paipu-empty";
            empty.textContent = capturedByUuid.size
                ? "当前日期范围内没有未导出的牌谱，请调整日期或取消“仅显示未导出”。"
                : `尚未捕获比赛场 ${TARGET_CONTEST_ID} 的牌谱。请刷新雀魂，从大会入口进入该比赛场并打开牌谱列表。`;
            rows.appendChild(empty);
            updateSelectionSummary();
            return;
        }

        for (const record of records) {
            const label = root.document.createElement("label");
            label.className = "santi-paipu-row";
            const checkbox = root.document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.value = record.uuid;
            checkbox.checked = true;
            checkbox.addEventListener("change", updateSelectionSummary);

            const details = root.document.createElement("span");
            details.className = "santi-paipu-row-details";
            const headline = root.document.createElement("span");
            headline.className = "santi-paipu-row-headline";
            headline.textContent = `${formatRecordTime(record.endTime || record.startTime)} · ${describeRoom(record)}`;
            const players = root.document.createElement("span");
            players.className = "santi-paipu-row-players";
            players.textContent = record.accounts.length
                ? record.accounts.map((account) => account.nickname).join(" / ")
                : "玩家信息未解析（不影响下载）";
            const uuid = root.document.createElement("span");
            uuid.className = "santi-paipu-row-uuid";
            uuid.textContent = record.uuid;
            details.append(headline, players, uuid);
            label.append(checkbox, details);
            rows.appendChild(label);
        }
        updateSelectionSummary();
    }

    function refreshVisibleRecords() {
        collectLegacyRecordMap();
        try {
            const fromTimestamp = localDateToTimestamp(root.document.getElementById("santi-paipu-from")?.value, false);
            const toTimestampExclusive = localDateToTimestamp(root.document.getElementById("santi-paipu-to")?.value, true);
            if (fromTimestamp >= toTimestampExclusive) {
                throw new Error("开始日期必须早于或等于结束日期");
            }
            const onlyNew = Boolean(root.document.getElementById("santi-paipu-only-new")?.checked);
            visibleRecords = filterRecords(Array.from(capturedByUuid.values()), {
                type: 4,
                contestId: TARGET_CONTEST_ID,
                fromTimestamp,
                toTimestampExclusive,
                onlyNew,
                exportedUuids: loadExportedUuids(),
            });
            renderRecords(visibleRecords);
            const mappingText = targetContestUniqueId
                ? `内部 ID ${targetContestUniqueId}`
                : "内部 ID 待识别";
            const capturedText = `比赛场 ${TARGET_CONTEST_ID}（${mappingText}）：本次会话捕获 ${capturedByUuid.size} 条，筛选后 ${visibleRecords.length} 条`;
            const guidance = targetContestUniqueId
                ? "请在该比赛场中打开牌谱列表。"
                : `尚未识别比赛场 ${TARGET_CONTEST_ID}，请刷新雀魂后从大会入口重新进入。`;
            setStatus(
                lastCaptureAt ? capturedText : `${capturedText}。${guidance}`,
                visibleRecords.length ? "success" : "info",
            );
        } catch (error) {
            visibleRecords = [];
            renderRecords([]);
            setStatus(error.message || String(error), "error");
        }
    }

    function getSelectedRecords() {
        const selectedUuids = new Set(
            Array.from(root.document.querySelectorAll(`#${IDS.rows} input[type="checkbox"]:checked`))
                .map((checkbox) => checkbox.value),
        );
        return visibleRecords.filter((record) => selectedUuids.has(record.uuid));
    }

    function createLinksText() {
        const selected = getSelectedRecords();
        if (!selected.length) {
            throw new Error("请至少选择一条牌谱");
        }
        return { selected, text: serializeLinks(selected) };
    }

    async function copyText(text) {
        if (typeof GM_setClipboard === "function") {
            GM_setClipboard(text, "text");
            return;
        }
        if (root.navigator.clipboard?.writeText) {
            await root.navigator.clipboard.writeText(text);
            return;
        }
        throw new Error("浏览器拒绝访问剪贴板，请改用“下载 links.txt”");
    }

    function downloadText(text) {
        const url = URL.createObjectURL(new Blob([text], { type: "text/plain;charset=utf-8" }));
        const link = root.document.createElement("a");
        link.href = url;
        link.download = "links.txt";
        link.style.display = "none";
        root.document.body.appendChild(link);
        link.click();
        link.remove();
        root.setTimeout(() => URL.revokeObjectURL(url), 1000);
    }

    async function exportByCopy() {
        try {
            const { selected, text } = createLinksText();
            await copyText(text);
            markExported(selected);
            refreshVisibleRecords();
            setStatus(`已复制 ${selected.length} 条牌谱链接`, "success");
        } catch (error) {
            setStatus(error.message || String(error), "error");
        }
    }

    function exportByDownload() {
        try {
            const { selected, text } = createLinksText();
            downloadText(text);
            markExported(selected);
            refreshVisibleRecords();
            setStatus(`已下载 links.txt（${selected.length} 条）`, "success");
        } catch (error) {
            setStatus(error.message || String(error), "error");
        }
    }

    function closeDialog() {
        root.document.getElementById(IDS.overlay)?.remove();
    }

    function addStyles(container) {
        if (root.document.getElementById("santi-paipu-export-styles")) {
            return;
        }
        const style = root.document.createElement("style");
        style.id = "santi-paipu-export-styles";
        style.textContent = `
            #${IDS.button} { position:fixed;right:18px;bottom:18px;z-index:2147483646;padding:10px 15px;border:0;border-radius:8px;background:#315c99;color:#fff;font:600 14px/1.2 sans-serif;box-shadow:0 3px 12px rgba(0,0,0,.35);cursor:pointer }
            #${IDS.button}:hover { background:#244a80 }
            #${IDS.overlay} { position:fixed;inset:0;z-index:2147483647;display:grid;place-items:center;padding:20px;background:rgba(0,0,0,.62);color:#1f2937;font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif }
            #${IDS.dialog} { width:min(860px,94vw);max-height:90vh;overflow:hidden;display:flex;flex-direction:column;background:#fff;border-radius:12px;box-shadow:0 18px 60px rgba(0,0,0,.45) }
            .santi-paipu-header,.santi-paipu-controls,.santi-paipu-actions,.santi-paipu-note { padding:14px 18px }
            .santi-paipu-header { display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #e5e7eb }
            .santi-paipu-header h2 { margin:0;font-size:19px }
            .santi-paipu-close { border:0;background:transparent;color:#64748b;font-size:24px;cursor:pointer }
            .santi-paipu-note { padding-block:10px;background:#f8fafc;color:#475569;border-bottom:1px solid #e5e7eb }
            .santi-paipu-controls { display:grid;grid-template-columns:repeat(5,minmax(120px,1fr));gap:10px;align-items:end }
            .santi-paipu-controls label { display:grid;gap:4px;color:#475569;font-size:12px }
            .santi-paipu-controls input,.santi-paipu-controls select { box-sizing:border-box;width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px;background:#fff;color:#111827 }
            .santi-paipu-checkbox { display:flex!important;grid-column:span 1;align-items:center;gap:7px!important;padding-bottom:8px }
            .santi-paipu-checkbox input { width:auto!important }
            .santi-paipu-primary,.santi-paipu-secondary { padding:9px 13px;border-radius:7px;cursor:pointer;font-weight:600 }
            .santi-paipu-primary { border:0;background:#315c99;color:#fff }
            .santi-paipu-secondary { border:1px solid #94a3b8;background:#fff;color:#334155 }
            #${IDS.status} { min-height:21px;padding:0 18px 10px;color:#475569 }
            #${IDS.status}[data-kind="success"] { color:#14753e }
            #${IDS.status}[data-kind="error"] { color:#b42318 }
            #${IDS.rows} { overflow:auto;min-height:140px;border-block:1px solid #e5e7eb }
            .santi-paipu-row { display:flex;gap:12px;padding:10px 18px;border-bottom:1px solid #f1f5f9;cursor:pointer }
            .santi-paipu-row:hover { background:#f8fafc }
            .santi-paipu-row input { margin-top:4px }
            .santi-paipu-row-details { min-width:0;display:grid;gap:2px }
            .santi-paipu-row-headline { font-weight:650;color:#0f172a }
            .santi-paipu-row-players { color:#334155 }
            .santi-paipu-row-uuid { color:#64748b;font:12px/1.35 ui-monospace,SFMono-Regular,Menlo,monospace }
            .santi-paipu-empty { padding:48px 18px;text-align:center;color:#64748b }
            .santi-paipu-actions { display:flex;flex-wrap:wrap;align-items:center;gap:9px }
            #${IDS.summary} { margin-right:auto;color:#475569 }
            @media (max-width:720px) { .santi-paipu-controls { grid-template-columns:1fr 1fr }.santi-paipu-checkbox { grid-column:1/-1 } }
        `;
        container.appendChild(style);
    }

    function openDialog() {
        if (root.document.getElementById(IDS.overlay)) {
            return;
        }
        collectLegacyRecordMap();
        const overlay = root.document.createElement("div");
        overlay.id = IDS.overlay;
        const dialog = root.document.createElement("section");
        dialog.id = IDS.dialog;
        dialog.setAttribute("role", "dialog");
        dialog.setAttribute("aria-modal", "true");
        dialog.setAttribute("aria-label", `雀魂比赛场 ${TARGET_CONTEST_ID} 牌谱链接导出器`);
        dialog.innerHTML = `
            <header class="santi-paipu-header"><h2>比赛场 ${TARGET_CONTEST_ID} 牌谱导出器</h2><button type="button" class="santi-paipu-close" aria-label="关闭">×</button></header>
            <div class="santi-paipu-note">固定捕获公开比赛场 ${TARGET_CONTEST_ID}（内部 ID ${TARGET_CONTEST_UNIQUE_ID}）。首次安装后刷新雀魂，从大会入口进入该比赛场并打开其牌谱列表；个人牌谱页中无法确认归属的记录不会导出。脚本只读取页面正常返回的数据，不会额外请求牌谱。</div>
            <div class="santi-paipu-controls">
                <label>牌谱类型<input type="text" value="大会战（固定）" readonly></label>
                <label>公开比赛场编号<input type="text" value="${TARGET_CONTEST_ID}" readonly></label>
                <label>开始日期<input id="santi-paipu-from" type="date"></label>
                <label>结束日期<input id="santi-paipu-to" type="date"></label>
                <label class="santi-paipu-checkbox"><input id="santi-paipu-only-new" type="checkbox" checked>仅显示未导出</label>
            </div>
            <div id="${IDS.status}" data-kind="info">准备读取已捕获的牌谱…</div>
            <div id="${IDS.rows}"></div>
            <footer class="santi-paipu-actions">
                <span id="${IDS.summary}">已选择 0 / 0 条牌谱</span>
                <button type="button" id="santi-paipu-refresh" class="santi-paipu-secondary">刷新列表</button>
                <button type="button" id="santi-paipu-select-all" class="santi-paipu-secondary">全选</button>
                <button type="button" id="santi-paipu-select-none" class="santi-paipu-secondary">清空选择</button>
                <button type="button" id="santi-paipu-copy" class="santi-paipu-primary">复制选中链接</button>
                <button type="button" id="santi-paipu-download" class="santi-paipu-primary">下载 links.txt</button>
            </footer>`;
        overlay.appendChild(dialog);
        root.document.body.appendChild(overlay);

        const today = new Date();
        const oneWeekAgo = new Date(today);
        oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);
        root.document.getElementById("santi-paipu-from").value = dateInputValue(oneWeekAgo);
        root.document.getElementById("santi-paipu-to").value = dateInputValue(today);

        dialog.querySelector(".santi-paipu-close").addEventListener("click", closeDialog);
        root.document.getElementById("santi-paipu-refresh").addEventListener("click", refreshVisibleRecords);
        root.document.getElementById("santi-paipu-copy").addEventListener("click", exportByCopy);
        root.document.getElementById("santi-paipu-download").addEventListener("click", exportByDownload);
        for (const id of ["santi-paipu-from", "santi-paipu-to", "santi-paipu-only-new"]) {
            root.document.getElementById(id).addEventListener("change", refreshVisibleRecords);
        }
        root.document.getElementById("santi-paipu-select-all").addEventListener("click", () => {
            dialog.querySelectorAll(`#${IDS.rows} input[type="checkbox"]`).forEach((checkbox) => { checkbox.checked = true; });
            updateSelectionSummary();
        });
        root.document.getElementById("santi-paipu-select-none").addEventListener("click", () => {
            dialog.querySelectorAll(`#${IDS.rows} input[type="checkbox"]`).forEach((checkbox) => { checkbox.checked = false; });
            updateSelectionSummary();
        });
        overlay.addEventListener("click", (event) => { if (event.target === overlay) closeDialog(); });
        refreshVisibleRecords();
    }

    function installButton() {
        if (!root.document.body || root.document.getElementById(IDS.button)) {
            return;
        }
        addStyles(root.document.head || root.document.body);
        const button = root.document.createElement("button");
        button.id = IDS.button;
        button.type = "button";
        button.addEventListener("click", openDialog);
        root.document.body.appendChild(button);
        updateButtonLabel();
    }

    installWebSocketHook();
    if (typeof GM_registerMenuCommand === "function") {
        GM_registerMenuCommand(`导出比赛场 ${TARGET_CONTEST_ID} 牌谱链接`, openDialog);
    }
    if (root.document.readyState === "loading") {
        root.document.addEventListener("DOMContentLoaded", installButton, { once: true });
    } else {
        installButton();
    }
    root.setInterval(() => {
        installWebSocketHook();
        installButton();
        collectLegacyRecordMap();
    }, 3000);
})(typeof globalThis !== "undefined" ? globalThis : this);
