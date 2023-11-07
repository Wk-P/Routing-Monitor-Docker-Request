'use strict';

var os = require("")


// for main server
const express = require('express');
// child process
const { fork } = require('child_process');

const path = require('path');

//Contents

// port in container
const PORT = 8080;
const HOST = '0.0.0.0';

//App

const app = express();
app.use(express.urlencoded({ extended: false }));
app.use(express.json());


app.post('/', (req, res) => {

	// run a new child process

	// for container
	const childScriptPath = path.join(path.dirname(__filename), 'child.js')
	const childProcess = fork(childScriptPath);


	// for test on linux host in Documents folder
	try {
		// const childProcess = fork('Documents/js/child.js');

		// send message to child process
		childProcess.send({ requestContent: req.body });
		
		// listen child process
		
		childProcess.on('message', (message) => {
			let cpu_usage = 0;
			// get CPU and MEM
			const cpus = os.cpus();
			for (let i = 0, len = cpus.length;i < len;i++) {
				var cpu = cpus[i], total = 0;
				for (let type in cpu.times) {
					total += cpu.times[type];
				}

				for (type in cpu.times) {
					cpu_usage = Math.round(100 * cpu.times[type] / total);
				}
			}
			res.json({
				counter: message,
				cpu: cpu_usage,
				mem: mem_usage
			});
			childProcess.kill();
		});
	} catch (err) {
		res.status(500).json({ error: 'Interal Server Error'});
	}
});

app.listen(PORT, HOST, () => {
	console.log(`Running on http://${HOST}:${PORT}`);
});
