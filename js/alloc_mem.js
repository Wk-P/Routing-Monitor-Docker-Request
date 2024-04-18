process.on('message', (size) => {
    const buf = allocMemeory(size);
    console.log(`Server has alloc size of ${size} memory`);
    buf.fill(0);
    console.log(`Buffer has been destroied`);
})

function allocMemeory(n) {
    try {
        return Buffer.alloc(n);
    }
    catch (error) {
        console.log(`ERROR => ${error}`);
    }
}