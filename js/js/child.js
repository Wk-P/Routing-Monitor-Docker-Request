process.on('message', (message) => {
    // code with time

    n = message.requestContent.number;
    // get result
    const result = simulateHeavyCalculation(n);


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

    while (num < n) {
        if (isPrime(num)) {
            count++;
        }
        num++;
    }
    return count;
}