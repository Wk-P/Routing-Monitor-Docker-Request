const { exec } = require('child_process');

process.on('message', (message) => {
    exec('df -h', (error, stdout, stderr) => {
        if (error) {
            console.log(`EXEC ERROR: ${error.message}`);
            process.send(-1);
            return;
        }
        if (stderr) {
            console.log(`CMD RES ERROR: ${stderr.message}`);
            process.send(-1);
            return;
        }
        const lines = stdout.split('\n');
        for (const line of lines) {
            if (line.includes('overlay')) {
                const words = line.split(/\s+/);
                const availableSpace = words[3];
                const match = availableSpace.match(/(\d+(\.\d+)?)([A-Za-z]+)/);
                if (match) {
                    const availableSpaceValue = match[1];
                    const availableSpaceUnit = match[2];
                    if (availableSpaceUnit == "K") {
                        process.send(availableSpaceValue * (2 ** 10) );
                    } else if (availableSpaceUnit == "M") {
                        process.send(availableSpaceValue * (2 ** 20));
                    } else if (availableSpaceValue == "G") {
                        process.send(availableSpaceValue * (2 * 30));
                    } else {
                        process.send(0);
                    }
                }
            }
        }
        console.log(`${stdout}`);
    });
});