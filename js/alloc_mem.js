process.on('message', (size) => {
    try {
        const array = allocMemeory(parseInt(size));
        console.log(`Server has alloc size of ${size} memory`);
        process.send(1);
    } catch (error) {
        console.log("IN ALLOC", error);
    }
})

function allocMemeory(n) {
    try {
        return Array(n);
    }
    catch (error) {
        console.log(`ERROR => ${error}`);
    }
}