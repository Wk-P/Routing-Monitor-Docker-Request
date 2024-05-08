const { exec } = require('child_process');
const { fs } = require('fs');

process.on('message', (size) => {
    const file_size = allocMemeory(parseInt(size));
    const file = fs.createWriteStream('example.txt', { flags: 'a' })
    let contents = "";
    for (let i = 0; i < file_size; i++) {
        contents += 'a';
    }
    file.write(contents);
    file.on('finish', () => {
        process.send("OK");
    });
    file.on("error", () => {
        process.send("ERROR");
    });
    file.end();
});