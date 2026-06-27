const keccak = require('keccak');
const { Worker, isMainThread, parentPort, workerData } = require('worker_threads');

// DeepSeek PoW Solver with multi-threading

function keccak256(s) {
    return keccak('keccak256').update(s).digest('hex');
}

function searchRange(prefix, target, start, end) {
    const k = keccak('keccak256');
    k.update(prefix);
    for (let i = start; i < end; i++) {
        if (k.copy().update(String(i)).digest('hex') === target) {
            return i;
        }
    }
    return null;
}

if (isMainThread) {
    // Main thread
    const challengeData = JSON.parse(process.argv[2] || '{}');

    if (!challengeData.challenge) {
        console.log('No challenge data');
        process.exit(1);
    }

    const { challenge, salt, difficulty, expire_at } = challengeData;
    const prefix = `${salt}_${expire_at}_`;

    console.log(`Solving PoW...`);
    console.log(`  Prefix: ${prefix}`);
    console.log(`  Target: ${challenge}`);
    console.log(`  Range: 0 - ${difficulty}`);

    // Use multiple workers
    const numWorkers = 8;
    const chunkSize = Math.ceil(difficulty / numWorkers);
    let found = false;

    for (let w = 0; w < numWorkers; w++) {
        const start = w * chunkSize;
        const end = Math.min((w + 1) * chunkSize, difficulty);

        const worker = new Worker(__filename, {
            workerData: { prefix, target: challenge, start, end }
        });

        worker.on('message', (answer) => {
            if (answer !== null && !found) {
                found = true;
                console.log(`\\nFound answer: ${answer}`);
                console.log(JSON.stringify({ answer }));
                process.exit(0);
            }
        });

        worker.on('error', (err) => {
            console.error(`Worker error: ${err}`);
        });
    }

    // Timeout
    setTimeout(() => {
        if (!found) {
            console.log('\\nNot found within timeout');
            console.log(JSON.stringify({ answer: null }));
            process.exit(1);
        }
    }, 60000);

} else {
    // Worker thread
    const { prefix, target, start, end } = workerData;
    const answer = searchRange(prefix, target, start, end);
    parentPort.postMessage(answer);
}