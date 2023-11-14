'use strict';

const os = require("os");

// for main server
const express = require('express');
// child process
const { fork } = require('child_process');

const path = require('path');
const { start } = require("repl");

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

		// Timer for child process run time

		// send message to child process
		childProcess.send({ requestContent: req.body });
		
		// listen child process
		
		childProcess.on('message', (data) => {
			// get and MEM
			const memUsage = (1 - (os.freemem() / os.totalmem()))

			childProcess.kill();

			res.json({
				data: data,
				mem: memUsage,
			});
		});
	} catch (err) {
		res.status(500).json({ error: 'Interal Server Error'});
	}
});

app.head('/', (req, res) => {
	try {
		const memUsage = (1 - (os.freemem() / os.totalmem()))
		const cpuUsage = process.cpuUsage()
		const cpuPercent = cpuUsage['user'] / (cpuUsage['system'] + cpuUsage['user'])
		
		res.setHeader("data", cpuPercent);
		res.setHeader("mem", memUsage);
		res.status(200).end();

	} catch (err) {
		res.status(500).json({error: 'Internal Server Error'});
	}
})

app.listen(PORT, HOST, () => {
	console.log(`Running on http://${HOST}:${PORT}`);
});
