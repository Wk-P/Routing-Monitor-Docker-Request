
// start time
const startTime = process.hrtime();





process.on('message', (message) => {
    // code with time
    // cpu usage
    const startUsage = process.cpuUsage();
    
    const n = message.requestContent.number;
    // get result

    const counterResult = simulateHeavyCalculation(n)


    const endUsage = process.cpuUsage(startUsage)
    const userUsage = endUsage['user']
    const systemUsage = endUsage['system']

    const cpuUsagePercent = (userUsage / (userUsage + systemUsage))

    // end time
    const elapsed = process.hrtime(startTime);

    const result = {
        number: n,
        counter: counterResult,
        cpuUsage: cpuUsagePercent,
        runtime: elapsed[0] * 1000 + elapsed[1] / 1000000
    }

    // send message to main process
    process.send(result);
})

// prime judgment
function isPrime(n) {
    if (n === 1) {
        return true;
    }
    for (let i = 2;i < n;i++) {
        if (n % i == 0) {
            return false;
        }
    }
    return true;
}

// prime conter 
function simulateHeavyCalculation(n) {
    // sum prime number 
    
    let count = 0;
    let num = 2;

    while (num <= n) {
        if (isPrime(num)) {
            count++;
        }
        num++;
    }
    return count;
}