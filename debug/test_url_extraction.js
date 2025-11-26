#!/usr/bin/env node
/**
 * 测试URL提取功能
 */

// 复制修改后的函数
function extractAllUrls(input)
{
    // 从文本中提取所有URL
    // 只匹配URL中合法的字符，遇到中文等字符时停止
    const urlPattern = /https?:\/\/[a-zA-Z0-9.\-_?=&#%/]+/g;
    const matches = input.match(urlPattern);
    return matches || [];
}

function normalizeUuid(input)
{
    let uuid = input.trim();
    if (!uuid)
        return "";

    // 先尝试从混杂文本中提取出标准URL
    // 只匹配URL中合法的字符，避免将中文等字符也包含进来
    const urlMatch = uuid.match(/https?:\/\/[a-zA-Z0-9.\-_?=&#%/]+/);
    if (urlMatch && urlMatch[0])
        uuid = urlMatch[0];

    // 去掉常见结尾标点
    uuid = uuid.replace(/[，,。．；;：:？?！!]+$/, "");

    if (uuid.includes("="))
    {
        const linkParts = uuid.split("=");
        const uuidParts = linkParts[linkParts.length - 1].split("_");
        uuid = uuidParts[0];
    }

    return uuid;
}

// 测试用例
const testCases = [
    {
        name: "连续中文分隔",
        input: "雀魂牌谱：https://mahjongsoul.game.yo-star.com/?paipu=251120-uuid1雀魂牌谱：https://mahjongsoul.game.yo-star.com/?paipu=251120-uuid2",
        expected: 2
    },
    {
        name: "混合中英文分隔",
        input: "雀魂牌谱：https://mahjongsoul.game.yo-star.com/?paipu=251120-uuid1看这个：https://mahjongsoul.game.yo-star.com/?paipu=251120-uuid2，还有https://mahjongsoul.game.yo-star.com/?paipu=251120-uuid3",
        expected: 3
    },
    {
        name: "单个URL带中文前缀",
        input: "雀魂牌谱：https://mahjongsoul.game.yo-star.com/?paipu=251120-uuid1",
        expected: 1
    },
    {
        name: "逗号分隔",
        input: "https://mahjongsoul.game.yo-star.com/?paipu=251120-uuid1, https://mahjongsoul.game.yo-star.com/?paipu=251120-uuid2",
        expected: 2
    },
    {
        name: "带下划线的编码UUID",
        input: "https://mahjongsoul.game.yo-star.com/?paipu=abc123_def456_2",
        expected: 1
    }
];

console.log("=".repeat(80));
console.log("URL提取测试");
console.log("=".repeat(80));

testCases.forEach((test, index) => {
    console.log(`\n测试 ${index + 1}: ${test.name}`);
    console.log(`输入: ${test.input.substring(0, 100)}${test.input.length > 100 ? '...' : ''}`);

    const urls = extractAllUrls(test.input);
    console.log(`\n提取到 ${urls.length} 个URL (期望 ${test.expected}):`);

    urls.forEach((url, i) => {
        const uuid = normalizeUuid(url);
        console.log(`  [${i + 1}] ${url}`);
        console.log(`      -> UUID: ${uuid}`);
    });

    if (urls.length === test.expected) {
        console.log(`✅ 通过`);
    } else {
        console.log(`❌ 失败: 期望 ${test.expected} 个，实际 ${urls.length} 个`);
    }
});

console.log("\n" + "=".repeat(80));
console.log("测试完成");
console.log("=".repeat(80));
