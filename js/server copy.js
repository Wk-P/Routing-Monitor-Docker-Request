'use strict';

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
	// check headers to get task type			
	const task_type = req.headers.task_type;
	const data = req.body;

	// calculate prime number
	if (task_type == "C") {
		// run a new child process	
		const primeScriptPath = path.join(path.dirname(__filename), 'prime_cal.js')
		const primeProcess = fork(primeScriptPath);
		
		// send message to child process
		primeProcess.send(data.number);
		
		// listen child process until finish request handle
		primeProcess.on('message', (result) => {
			// get and MEM
			primeProcess.kill();
			res.json({result: result});
		});
	} else if (task_type == "M") {
		try {
			// run a new child process	
			const memScriptPath = path.join(path.dirname(__filename), 'alloc_mem.js')
			const memProcess = fork(memScriptPath);
			
			// send message to child process
			memProcess.send(data.size);
			
			// listen child process until finish request handle
			memProcess.on('message', (return_code) => {
				// get and MEM
				console.log(`return code => ${return_code}`);
				memProcess.kill();
				res.json({result: `memory alloc finished, return code => ${return_code}`});
			});
		} catch (error) {
			res.status(500).json({ error: error});
		}
	} else if (task_type == "H") {
		const hddScriptPath = path.join(path.dirname(__filename), 'hdd_stats.js')
		const hddProcess = fork(hddScriptPath);

		hddProcess.send("fetch");
		
		hddProcess.on("message", (usage) => {
			console.log(`HDD usage => ${usage}`);
			hddProcess.kill();
			res.json({result: usage});
		})
	} else {
		res.json({result: "error"});
	}
})

app.listen(PORT, HOST, () => {
	console.log(`Running on http://${HOST}:${PORT}`);
});
