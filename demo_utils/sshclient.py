import paramiko
import re

def ssh_command(host, port, username, password, command):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, port=port, username=username, password=password)
    stdin, stdout, stderr = client.exec_command(command)
    output = stdout.read().decode()
    error = stderr.read().decode()
    client.close()
    return output, error


if __name__ == "__main__":
    host = "10.0.2.7"
    port = 22
    username = "soar"
    password = "123321"
    command = "df --total /var/lib/docker/"
    output, error = ssh_command(host, port, username, password, command)

    print(output)

    matches = re.findall(r"([\d]+%) -", output)
    if matches:
        print(matches[0])
    else:
        print(matches)