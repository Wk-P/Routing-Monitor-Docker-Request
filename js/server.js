'use strict';

const os = require('os');

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

function getCpuUsage() {
	const cpus = os.cpus();
	let total = 0;
	let idle = 0;
	for (const cpu of cpus) {
		total += cpu.times.user + cpu.times.system + cpu.times.idle;
		idle += cpu.times.idle;
	}

	const idleCpuUsage = (idle / total) * 100;
	const cpuUsage = 100 - idleCpuUsage.toFixed(2);

	return cpuUsage;
}

try {
	app.post('/', (req, res) => {
		
		// run a new child process	

		// for container
		const childScriptPath = path.join(path.dirname(__filename), 'child.js')

		const childProcess = fork(childScriptPath);

		// for test on linux host in Documents folder


		// Timer for child process run time

		// send message to child process
		childProcess.send({ requestContent: req.body });
		
		// listen child process
		
		childProcess.on('message', (data) => {
			// get and MEM
			const memUsage = (1 - (os.freemem() / os.totalmem()))

			childProcess.kill();
			
			res.json(data);
		});
		
	})
} catch (err) {
	res.status(500).json({ error: 'Interal Server Error'});
}

app.head('/', (req, res) => {
	try {
		const memUsage = (1 - (os.freemem() / os.totalmem()))
		const cpuPercent = getCpuUsage()
		
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
