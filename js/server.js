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

try {
	app.post('/', (req, res) => {
		// check headers to get task type
		const task_type = req.headers.task_type;
		const data = req.body;


		// calculate prime number
		if (task_type == "C") {
			// run a new child process	
			const childScriptPath = path.join(path.dirname(__filename), 'prime_cal.js')
			const childProcess = fork(childScriptPath);
			
			// send message to child process
			childProcess.send(data.number);
			
			// listen child process until finish request handle
			childProcess.on('message', (result) => {
				// get and MEM
				childProcess.kill();
				res.json({result: result});
			});
		} else if (task_type == "M") {
			// run a new child process	
			const childScriptPath = path.join(path.dirname(__filename), 'alloc_mem.js')
			const childProcess = fork(childScriptPath);
			
			// send message to child process
			childProcess.send(data.size);
			
			// listen child process until finish request handle
			childProcess.on('message', (data) => {
				// get and MEM
				childProcess.kill();
				res.json({result: "memory alloc finished"});
			});
		} else if (task_type == "H") {
			res.json({result: "copy finished"});
		} else {
			console.log("Error");
		}
	})
} catch (err) {
	res.status(500).json({ error: 'Interal Server Error'});
}

app.listen(PORT, HOST, () => {
	console.log(`Running on http://${HOST}:${PORT}`);
});
