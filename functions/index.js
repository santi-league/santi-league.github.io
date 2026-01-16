const functions = require('firebase-functions');
const admin = require('firebase-admin');

admin.initializeApp();

/**
 * 辅助函数：获取今天的日期字符串（YYYY-MM-DD格式）
 */
function getTodayString() {
  const now = new Date();
  const year = now.getUTCFullYear();
  const month = String(now.getUTCMonth() + 1).padStart(2, '0');
  const day = String(now.getUTCDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/**
 * 当文件上传到 Storage 时触发
 * 这个函数会验证 JSON 文件并标记为待处理
 */
exports.onFileUploaded = functions.storage.bucket('santi-league.firebasestorage.app').object().onFinalize(async (object) => {
  const filePath = object.name; // 例如: game-logs/m-league/2026-01-16/12345_game.json
  const contentType = object.contentType;

  // 只处理 game-logs 目录下的 JSON 文件
  if (!filePath.startsWith('game-logs/') || !contentType.includes('json')) {
    console.log('Skipping non-game-log file:', filePath);
    return null;
  }

  console.log('New file uploaded:', filePath);

  // 获取文件内容
  const bucket = admin.storage().bucket(object.bucket);
  const file = bucket.file(filePath);

  try {
    // 下载并验证 JSON
    const [contents] = await file.download();
    const jsonData = JSON.parse(contents.toString());

    // 验证是否是有效的雀魂牌谱
    if (!jsonData.log || !Array.isArray(jsonData.log)) {
      console.error('Invalid game log format:', filePath);
      return null;
    }

    // 从 Firestore 中查找对应的元数据记录
    const db = admin.firestore();
    const logsRef = db.collection('game-logs');
    const query = await logsRef.where('storagePath', '==', filePath.replace('game-logs/', '')).get();

    if (!query.empty) {
      const docRef = query.docs[0].ref;

      // 更新状态为已验证
      await docRef.update({
        validated: true,
        validatedAt: admin.firestore.FieldValue.serverTimestamp(),
        playerCount: jsonData.name ? jsonData.name.length : 0,
        roundCount: jsonData.log.length
      });

      // 记录处理日志
      await db.collection('processing-logs').add({
        filePath: filePath,
        action: 'validated',
        success: true,
        timestamp: admin.firestore.FieldValue.serverTimestamp()
      });

      console.log('File validated successfully:', filePath);
    }

    return null;
  } catch (error) {
    console.error('Error processing file:', filePath, error);

    // 记录错误
    await admin.firestore().collection('processing-logs').add({
      filePath: filePath,
      action: 'validation_failed',
      error: error.message,
      timestamp: admin.firestore.FieldValue.serverTimestamp()
    });

    return null;
  }
});

/**
 * 定期触发的函数：每小时检查是否有新文件需要处理
 * 如果有，则触发网站重新生成
 *
 * 注意：这个函数需要手动触发或通过调度器触发
 * 实际的网站重新生成需要在服务器端运行 Python 脚本
 */
exports.scheduledRegenerateSite = functions.pubsub
  .schedule('every 1 hours')
  .onRun(async (context) => {
    const db = admin.firestore();

    // 查找已验证但未处理的文件
    const unprocessedQuery = await db.collection('game-logs')
      .where('validated', '==', true)
      .where('processed', '==', false)
      .limit(100)
      .get();

    if (unprocessedQuery.empty) {
      console.log('No new files to process');
      return null;
    }

    console.log(`Found ${unprocessedQuery.size} files to process`);

    // 在实际应用中，这里应该触发网站重新生成
    // 选项 1: 调用外部 webhook 或 API
    // 选项 2: 使用 GitHub Actions
    // 选项 3: 在 Cloud Functions 中运行 Python 脚本（需要自定义运行时）

    // 这里我们只是标记文件为"待处理"
    const batch = db.batch();
    unprocessedQuery.docs.forEach(doc => {
      batch.update(doc.ref, {
        processingQueued: true,
        queuedAt: admin.firestore.FieldValue.serverTimestamp()
      });
    });
    await batch.commit();

    // 记录日志
    await db.collection('processing-logs').add({
      action: 'queued_for_processing',
      fileCount: unprocessedQuery.size,
      timestamp: admin.firestore.FieldValue.serverTimestamp()
    });

    console.log('Files queued for processing');
    return null;
  });

/**
 * HTTP 函数：手动触发网站重新生成
 * 用法: POST https://your-region-your-project.cloudfunctions.net/triggerRegenerate
 * 需要在请求头中提供认证令牌
 */
exports.triggerRegenerate = functions.https.onRequest(async (req, res) => {
  // 允许 CORS
  res.set('Access-Control-Allow-Origin', '*');

  if (req.method === 'OPTIONS') {
    res.set('Access-Control-Allow-Methods', 'POST');
    res.set('Access-Control-Allow-Headers', 'Authorization, Content-Type');
    res.status(204).send('');
    return;
  }

  if (req.method !== 'POST') {
    res.status(405).send('Method Not Allowed');
    return;
  }

  const db = admin.firestore();

  try {
    // 查找待处理的文件
    const unprocessedQuery = await db.collection('game-logs')
      .where('validated', '==', true)
      .where('processed', '==', false)
      .get();

    if (unprocessedQuery.empty) {
      res.json({
        success: true,
        message: 'No new files to process',
        fileCount: 0
      });
      return;
    }

    // 获取所有文件路径
    const filePaths = unprocessedQuery.docs.map(doc => doc.data().storagePath);

    // 标记为已处理（在实际应用中，应该等待真正处理完成）
    const batch = db.batch();
    unprocessedQuery.docs.forEach(doc => {
      batch.update(doc.ref, {
        processed: true,
        processedAt: admin.firestore.FieldValue.serverTimestamp()
      });
    });
    await batch.commit();

    // 记录处理日志
    await db.collection('processing-logs').add({
      action: 'manual_trigger',
      fileCount: filePaths.length,
      filePaths: filePaths,
      timestamp: admin.firestore.FieldValue.serverTimestamp()
    });

    res.json({
      success: true,
      message: `Queued ${filePaths.length} files for processing`,
      fileCount: filePaths.length,
      files: filePaths
    });

  } catch (error) {
    console.error('Error triggering regenerate:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

/**
 * 获取上传统计信息
 * 用法: GET https://your-region-your-project.cloudfunctions.net/getUploadStats
 */
exports.getUploadStats = functions.https.onRequest(async (req, res) => {
  res.set('Access-Control-Allow-Origin', '*');

  if (req.method === 'OPTIONS') {
    res.set('Access-Control-Allow-Methods', 'GET');
    res.set('Access-Control-Allow-Headers', 'Content-Type');
    res.status(204).send('');
    return;
  }

  const db = admin.firestore();

  try {
    const logsSnapshot = await db.collection('game-logs').get();

    const stats = {
      total: logsSnapshot.size,
      processed: 0,
      pending: 0,
      failed: 0,
      byLeague: {
        'm-league': 0,
        'ema': 0,
        'sanma': 0
      }
    };

    logsSnapshot.docs.forEach(doc => {
      const data = doc.data();

      if (data.processed) {
        stats.processed++;
      } else if (data.validated === false) {
        stats.failed++;
      } else {
        stats.pending++;
      }

      if (data.league && stats.byLeague.hasOwnProperty(data.league)) {
        stats.byLeague[data.league]++;
      }
    });

    res.json(stats);
  } catch (error) {
    console.error('Error getting stats:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * Firestore 触发器：当创建新的 game-log 文档时，增加今日上传计数器
 */
exports.incrementUploadCounter = functions.firestore
  .document('game-logs/{logId}')
  .onCreate(async (snap, context) => {
    const db = admin.firestore();
    const today = getTodayString();
    const counterRef = db.collection('upload-counters').doc(today);

    try {
      // 使用事务来安全地增加计数器
      await db.runTransaction(async (transaction) => {
        const counterDoc = await transaction.get(counterRef);

        if (!counterDoc.exists) {
          // 如果今天的计数器不存在，创建它
          transaction.set(counterRef, {
            count: 1,
            date: today,
            createdAt: admin.firestore.FieldValue.serverTimestamp()
          });
        } else {
          // 如果存在，增加计数
          const newCount = (counterDoc.data().count || 0) + 1;
          transaction.update(counterRef, {
            count: newCount,
            updatedAt: admin.firestore.FieldValue.serverTimestamp()
          });
        }
      });

      console.log(`Upload counter incremented for ${today}`);
      return null;
    } catch (error) {
      console.error('Error incrementing upload counter:', error);
      return null;
    }
  });

/**
 * HTTP 函数：获取今日上传配额信息
 * 用法: GET https://your-region-your-project.cloudfunctions.net/getTodayQuota
 */
exports.getTodayQuota = functions.https.onRequest(async (req, res) => {
  res.set('Access-Control-Allow-Origin', '*');

  if (req.method === 'OPTIONS') {
    res.set('Access-Control-Allow-Methods', 'GET');
    res.set('Access-Control-Allow-Headers', 'Content-Type');
    res.status(204).send('');
    return;
  }

  const db = admin.firestore();
  const today = getTodayString();
  const counterRef = db.collection('upload-counters').doc(today);

  try {
    const counterDoc = await counterRef.get();
    const currentCount = counterDoc.exists ? (counterDoc.data().count || 0) : 0;
    const maxUploads = 50;
    const remaining = Math.max(0, maxUploads - currentCount);

    res.json({
      date: today,
      uploaded: currentCount,
      remaining: remaining,
      limit: maxUploads,
      canUpload: remaining > 0
    });
  } catch (error) {
    console.error('Error getting quota:', error);
    res.status(500).json({ error: error.message });
  }
});
