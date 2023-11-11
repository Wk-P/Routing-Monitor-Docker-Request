process.on('message', (message) => {
    // code with time

    const n = message.requestContent.number;
    // get result

    const startTime = process.hrtime();
    const counterResult = simulateHeavyCalculation(n)
    const elapsed = process.hrtime(startTime);

    const currentUsage = process.cpuUsage()
    const userUsage = currentUsage['user']
    const systemUsage = currentUsage['system']

    const cpuUsagePercent = (userUsage / (userUsage + systemUsage))



    const result = {
        number: n,
        counter: counterResult,
        cpuUsage: cpuUsagePercent,
        runtime: elapsed[0] * 1000 + elapsed[1] / 1e6
    }

    // send message to main process
    process.send(result);
})

// prime judgment
function isPrime(n) {
    if (n === 1) {
        return false;
    }
    else {
        for (let i = 2;i < n;i++) {
            if (n % i == 0) {
                return false;
            }
        }
        return true;
    }
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