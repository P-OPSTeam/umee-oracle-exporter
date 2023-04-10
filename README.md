# Umee Oracle Exporter

## Requirements

- python 3.10.x

## Installation

```
cd ~
git clone https://github.com/P-OPSTeam/umee-oracle-exporter.git
sudo apt install software-properties-common -y
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3 python3-virtualenv python3.10-distutils
cd umee-oracle-exporter
virtualenv -p /usr/bin/python3 .venv
source .venv/bin/activate
curl -sS https://bootstrap.pypa.io/get-pip.py | python3
pip install -r requirements.txt
```

## fill up the .env

```
cp .env.example .env
```

Edit .env accordingly

## Run it

```
python exporter.py
```

## As a service

```
sudo cp umee-oracle-exporter.service /etc/systemd/system/
sudo sed -i "s:<home>:${HOME}:g" /etc/systemd/system/umee-oracle-exporter.service
sudo sed -i "s/<user>/${USER}/g" /etc/systemd/system/umee-oracle-exporter.service
sudo systemctl daemon-reload 
sudo systemctl enable umee-oracle-exporter
sudo systemctl start umee-oracle-exporter
```

# Test it

```
curl -s localhost:9877/metric | grep miss
```
# TODO

- [] write more documentation
