const { fs } = require('fs');

process.on('message', (size) => {
    const file_size = parseInt(size);
    let contents = "";
    for (let i = 0; i < file_size; i++) {
        contents += 'a';
    }
    fs.appendFile('./example.txt', contents, err => {
        if (err) {
            process.send("error");
        } else {
            process.send("OK");
        }
    })
});