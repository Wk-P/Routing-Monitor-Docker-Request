process.on('message', (number) => {
    // result is a integer number
    const result = simulateHeavyCalculation(parseInt(number));

    // send result to main process
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
