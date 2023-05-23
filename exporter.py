"""Application exporter"""

import os
import time
from prometheus_client import start_http_server, Gauge, Enum
import requests
from requests.exceptions import HTTPError
from datetime import datetime, timedelta, timezone
import argparse
from dotenv import load_dotenv
import json
import traceback

def http_json_call(url):
    try:
        r = requests.get(url)
        r.raise_for_status()
    except HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')  # Python 3.6
    except Exception as err:
        print(f'Other error occurred: {err}')  # Python 3.6
    else:
        return json.loads(r.content)

def argsparse():

   parser = argparse.ArgumentParser(description="Umee Oracle Exporter")
   parser.add_argument( "-v", "--verbose", help="increase output/debug \
                       verbosity and details, default is false",
                        action="store_true")
   args = parser.parse_args()
   return args

def get_timestamp(dtstring):
    dt = datetime.strptime(dtstring, '%Y-%m-%dT%H:%M:%SZ')

    # convert datetime to time-aware timezone at UTC
    # so correct timestamp is returned
    dt = dt.replace(tzinfo=timezone.utc)

    # Return the time in seconds since the epoch 
    return dt.timestamp()


class AppMetrics:
    """
    Representation of Prometheus metrics and loop to fetch and transform
    application metrics into Prometheus metrics.
    """

    def __init__(self, polling_interval_seconds=15, valoper="", 
                 api_endpoint="http://localhost:1317",
                 blocktime = 5,verbose=False) :
        self.polling_interval_seconds = polling_interval_seconds
        self.valoper = valoper
        self.verbose = verbose
        self.apiendpoint = api_endpoint
        self.blocktime = blocktime

        # Prometheus metrics to collect
        self.window_progress = Gauge("window_progress", "current slash window \
progress, block number in the current window")
        self.slash_window = Gauge("slash_window", "number of blocks during which \
validators can miss votes")
        self.minvalidperwindow = Gauge("minvalidperwindow", "percentage of \
misses trigering a slash at the end of the slash window")
        self.miss_counter = Gauge("miss_counter", "current miss counter for \
a given validator", ["valoper"])
        self.slash_fraction = Gauge("slash_fraction", "slashed fraction")
        self.feeder_account = Gauge("feeder_account", "current delegate for \
a given validator", ["valoper", "feeder"])
        self.miss_rate = Gauge("miss_rate", "current miss rate", ["valoper"])
        self.next_window_start = Gauge("next_window_start", "timestamp of \
the next estimated windows start in UTC")
        self.vote_period = Gauge("vote_period", "Number of block to submit \
the next vote")
        self.last_block_vote = Gauge("last_block_vote", "Last block validator \
voted", ["valoper"])
        self.symbols_count = Gauge("symbols_count", "Number of symbols the \
feeder is supposed to broadcast")


    def run_metrics_loop(self):
        """Metrics fetching loop"""

        while True:
            self.fetch()
            time.sleep(self.polling_interval_seconds)

    def fetch(self):
        """
        Get metrics from application and refresh Prometheus metrics with
        new values.
        """

        try:
            # Fetch oracle params
            url=f"{self.apiendpoint}/umee/oracle/v1/params"
            oracle_config = http_json_call(url=url)["params"]
            self.slash_window.set(oracle_config['slash_window'])
            self.minvalidperwindow.set(oracle_config['min_valid_per_window'])
            self.slash_fraction.set(oracle_config['slash_fraction'])
            self.vote_period.set(oracle_config['vote_period'])
            self.symbols_count.set(len(oracle_config['accept_list']))
            
            # can you generate a snippet for counting the number of element in the array


            # Fetch current windows progress
            url=f"{self.apiendpoint}/umee/oracle/v1/slash_window"
            slash_window = http_json_call(url=url)
            self.window_progress.set(slash_window['window_progress'])

            # Fetch validator current miss counter
            url=f"{self.apiendpoint}/umee/oracle/v1/validators/{self.valoper}/miss"
            current_miss = http_json_call(url=url)
            self.miss_counter.labels(valoper=self.valoper).set(current_miss['miss_counter'])

            # Fetch feeder account associated with the validator
            url=f"{self.apiendpoint}/umee/oracle/v1/validators/{self.valoper}/feeder"
            feeder_account = http_json_call(url=url)
            self.feeder_account.labels(valoper=self.valoper, 
                                       feeder=feeder_account['feeder_addr']).set(1)

            # calculate the miss rate
            self.miss_rate.labels(valoper=self.valoper).set(
                int(current_miss['miss_counter']) / 
                (int(slash_window['window_progress']) * 
                len(oracle_config['accept_list'])))

            # calculate the estimated windows start
            dt=datetime.today() + timedelta(seconds=(((int(oracle_config['slash_window']) / 
                                                      int(oracle_config['vote_period'])) - 
                                                      int(slash_window['window_progress']) + 1 ) * 
                                                      int(self.blocktime) * 
                                                      int(oracle_config['vote_period'])))
            dt=dt.replace(tzinfo=timezone.utc)
            self.next_window_start.set(dt.timestamp())

            try:
              # Fetch prevote aggregate
              url=f"{self.apiendpoint}/umee/oracle/v1/validators/{self.valoper}/aggregate_prevote"
              prevotes = http_json_call(url=url)
              self.last_block_vote.labels(valoper=self.valoper).set(prevotes["aggregate_prevote"]["submit_block"])
            except: # codespace oracle code 11: no aggregate prevote: umeevaloperxxxxx
                print(f"{datetime.today()} Error aggregate_prevote" + str(e))
                pass # during update, the prevote aggregate is not available
        except Exception as e:
            print(traceback.format_exc())
            print(f"{datetime.today()} Error trying to fetch data with error:" + str(e))
            
def main():
    """Main entry point"""

    args = argsparse()
    verbose = args.verbose

    load_dotenv() # take environment variables from .env
    valoper=os.getenv('VALOPER')
    polling_interval_seconds = int(os.getenv("POLLING_INTERVAL_SECONDS", "15"))
    exporter_port = int(os.getenv("EXPORTER_PORT", "9877"))
    api_endpoint = os.getenv("API_ENDPOINT", "https://api.athena.main.network.umee.cc")
    blocktime = os.getenv("BLOCKTIME", "5")

    print("Umee Oracle Exporter started and now listening on port " + str(exporter_port))

    app_metrics = AppMetrics(
        polling_interval_seconds=polling_interval_seconds,
        valoper=valoper,
        api_endpoint=api_endpoint,
        blocktime=blocktime,
        verbose=verbose
    )
    start_http_server(exporter_port)
    app_metrics.run_metrics_loop()

if __name__ == "__main__":
    main()
