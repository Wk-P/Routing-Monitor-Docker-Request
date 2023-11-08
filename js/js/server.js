'use strict';

const os = require("os");

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
		// send message to child process
		childProcess.send({ requestContent: req.body });
		
		// listen child process
		
		childProcess.on('message', (data) => {
			// get and MEM
			const memUsage = (1 - (os.freemem() / os.totalmem()))

			res.json({
				data: data,
				mem: memUsage
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
