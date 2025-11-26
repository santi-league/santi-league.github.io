#!/usr/bin/env node
/**
 * 测试UUID提取功能
 */

function extractAllUuids(input)
{
    // 按"https"分段，然后从每段中提取UUID
    const segments = input.split('https');
    const uuids = [];

    // UUID格式: 251125-7c9b5806-bb5b-4cf3-81f4-8cdf1f60bc37
    const uuidPattern = /\d{6}-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/g;

    segments.forEach(segment => {
        // 用全局匹配，一段里可能有多个UUID
        const matches = segment.match(uuidPattern);
        if (matches) {
            uuids.push(...matches);
        }
    });

    return uuids;
}

// 测试用例
const testCases = [
    {
        name: "连续中文分隔的完整格式",
        input: "雀魂牌谱：251125-7c9b5806-bb5b-4cf3-81f4-8cdf1f60bc37_a259233423雀魂牌谱：251125-8d1c2345-aa1b-4cf3-81f4-9cdf1f60bc38_b123456789",
        expected: 2,
        expectedUuids: [
            "251125-7c9b5806-bb5b-4cf3-81f4-8cdf1f60bc37",
            "251125-8d1c2345-aa1b-4cf3-81f4-9cdf1f60bc38"
        ]
    },
    {
        name: "混合URL和纯UUID",
        input: "https://mahjongsoul.game.yo-star.com/?paipu=251125-7c9b5806-bb5b-4cf3-81f4-8cdf1f60bc37_a259233423看这个251125-8d1c2345-aa1b-4cf3-81f4-9cdf1f60bc38_b123456789",
        expected: 2,
        expectedUuids: [
            "251125-7c9b5806-bb5b-4cf3-81f4-8cdf1f60bc37",
            "251125-8d1c2345-aa1b-4cf3-81f4-9cdf1f60bc38"
        ]
    },
    {
        name: "单个UUID",
        input: "251125-7c9b5806-bb5b-4cf3-81f4-8cdf1f60bc37",
        expected: 1,
        expectedUuids: [
            "251125-7c9b5806-bb5b-4cf3-81f4-8cdf1f60bc37"
        ]
    },
    {
        name: "带下划线后缀的UUID",
        input: "251125-7c9b5806-bb5b-4cf3-81f4-8cdf1f60bc37_a259233423",
        expected: 1,
        expectedUuids: [
            "251125-7c9b5806-bb5b-4cf3-81f4-8cdf1f60bc37"
        ]
    },
    {
        name: "逗号分隔",
        input: "251125-7c9b5806-bb5b-4cf3-81f4-8cdf1f60bc37, 251125-8d1c2345-aa1b-4cf3-81f4-9cdf1f60bc38",
        expected: 2,
        expectedUuids: [
            "251125-7c9b5806-bb5b-4cf3-81f4-8cdf1f60bc37",
            "251125-8d1c2345-aa1b-4cf3-81f4-9cdf1f60bc38"
        ]
    },
    {
        name: "换行分隔",
        input: "251125-7c9b5806-bb5b-4cf3-81f4-8cdf1f60bc37\n251125-8d1c2345-aa1b-4cf3-81f4-9cdf1f60bc38\n251125-9e2d3456-bb2c-4cf3-81f4-acdf1f60bc39",
        expected: 3,
        expectedUuids: [
            "251125-7c9b5806-bb5b-4cf3-81f4-8cdf1f60bc37",
            "251125-8d1c2345-aa1b-4cf3-81f4-9cdf1f60bc38",
            "251125-9e2d3456-bb2c-4cf3-81f4-acdf1f60bc39"
        ]
    }
];

console.log("=".repeat(80));
console.log("UUID提取测试");
console.log("=".repeat(80));

let passed = 0;
let failed = 0;

testCases.forEach((test, index) => {
    console.log(`\n测试 ${index + 1}: ${test.name}`);
    console.log(`输入: ${test.input.substring(0, 100)}${test.input.length > 100 ? '...' : ''}`);

    const uuids = extractAllUuids(test.input);
    console.log(`\n提取到 ${uuids.length} 个UUID (期望 ${test.expected}):`);

    uuids.forEach((uuid, i) => {
        const isCorrect = test.expectedUuids[i] === uuid ? '✓' : '✗';
        console.log(`  [${i + 1}] ${uuid} ${isCorrect}`);
        if (test.expectedUuids[i] && test.expectedUuids[i] !== uuid) {
            console.log(`      期望: ${test.expectedUuids[i]}`);
        }
    });

    const allMatch = uuids.length === test.expected &&
                     uuids.every((uuid, i) => uuid === test.expectedUuids[i]);

    if (allMatch) {
        console.log(`✅ 通过`);
        passed++;
    } else {
        console.log(`❌ 失败`);
        failed++;
    }
});

console.log("\n" + "=".repeat(80));
console.log(`测试完成: ${passed} 通过, ${failed} 失败`);
console.log("=".repeat(80));
