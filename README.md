# ASVDb

Python and command-line interface to a ASV "database", as described [here](https://asv.readthedocs.io/en/stable/dev.html?highlight=%24results_dir#benchmark-suite-layout-and-file-formats).

The `asvdb` CLI can be used for inspecting the contents of a database, creating new databases based on specific contents of others, editing the contents of an existing database, and possibly more.

The `asvdb` python library can be used for the same tasks as the CLI, but is intended to be called directly from another application (benchmarking tool, notebook, test code, etc.) and is designed for adding new benchmark results easily.

![asvdb-based benchmarking design diagram](https://docs.google.com/drawings/d/e/2PACX-1vRIxIV02BWh5tbJkF1fL368m0JvepZKqcD0oxYQNIQesgda1qsFo_zlmygRh5unfFOWwsTYGaYgUzmA/pub?w=960&h=720)

## `asvdb` CLI:
From the help:
```
usage: asvdb [-h] [--version] [--read-from PATH] [--list-keys] [--filter EXPR]
             [--exec CMD] [--exec-once CMD] [--print PRINTEXPR]
             [--write-to PATH]

Examine or update an ASV 'database' row-by-row.

optional arguments:
  -h, --help         show this help message and exit
  --version          Print the current verison of asvdb and exit.
  --read-from PATH   Path to ASV db dir to read data from.
  --list-keys        List all keys found in the database to STDOUT.
  --filter EXPR      Action which filters the current results based on the
                     evaluation of EXPR.
  --exec CMD         Action which executes CMD on each of the current results.
  --exec-once CMD    Action which executes CMD once (is not executed for each
                     result).
  --print PRINTEXPR  Action which evaluates PRINTEXPR in a print() statement
                     for each of the current results.
  --write-to PATH    Path to ASV db dir to write data to. PATH is created if
                     it does not exist.

The database is read and each 'row' (an individual result and its context) has
the various expressions evaluated in the context of the row (see --list-keys for
all the keys that can be used in an expression/command).  Each action can
potentially modify the list of rows for the next action. Actions can be chained
to perform complex queries or updates, and all actions are performed in the
order which they were specified on the command line.

The --exec-once action is an exception in that it does not execute on every row,
but instead only once in the context of the global namespace. This allows for
the creation of temp vars or other setup steps that can be used in
expressions/commands in subsequent actions. Like other actions, --exec-once can
be chained with other actions and called multiple times.

The final list of rows will be written to the destination database specified by
--write-to, if provided. If the path to the destination database does not exist,
it will be created. If the destination database does exist, it will be updated
with the results in the final list of rows.

Remember, an ASV database stores results based on the commitHash, so modifying
the commitHash for a result and writing it back to the same databse results in a
new, *additional* result as opposed to a modified one. All updates to the
database specified by --write-to either modify an existing result or add new
results, and results cannot be removed from a database. In order to effectively
remove results, a user can --write-to a new database with only the results they
want, then replace the original with the new using file system commands (rm the
old one, mv the new one to the old one's name, etc.)
```

## Examples:

### `asvdb` CLI tool
- Print the number of results in the database
```
user@machine> asvdb --read-from=./my_asv_dir \
  --exec-once="i=0" \
  --exec="i+=1" \
  --exec-once="print(i)"

2040
```
This uses `--exec-once` to initialize a var `i` to 0, then execute `i+=1` for each row (result), then `--exec-once` to print the final value of `i`. `--exec-once` only executes once as opposed to once-per-row.
An easier way using shell tools is to just print any key from a row (`funcName` for example) and count the number of lines printed. This works because `--print` is executed for every row, and each row represents one unique result:
```
user@machine> asvdb --read-from=./my_asv_dir --print="funcName" | wc -l

2040
```

- Check which branches are in the database
```
user@machine> asvdb --read-from=./my_asv_dir \
  --exec-once="branches=set()" \
  --exec="branches.add(branch)" \
  --exec-once="print(branches)"

{'branch-0.14', 'branch-0.15'}
```
   or slightly easier using shell tools:
```
user@machine> asvdb --read-from=./my_asv_dir --print="branch" | sort -u

branch-0.14
branch-0.15
```
In the above example, the `sort -u` is used to limit the output to only unique items. As mentioned, `asvdb` actions (except `--exec-once`) operate on every row, so the print expression will be applied to each row, resulting in 2040 prints (one per result).

- Get the results for a specific benchmark, with specific param values, for all commits. **This is a quick and easy way to check for a regression right from your shell!**
```
user@machine> asvdb --read-from=./my_asv_dir \
  --filter="funcName=='bench_algos.bench_pagerank_time' \
      and argNameValuePairs==[('dataset', '../datasets/csv/directed/cit-Patents.csv'), ('managed_mem', 'False'), ('pool_allocator', 'True')]" \
  --print="commitHash, result, unit"

c29c3e359d1d945ef32b6867809a331f460d3e46 0.09114686909640984 seconds
8f077b8700cc5d1b4632c429557eaed6057e03a1 0.09145867270462334 seconds
ff154939008654e62b6696cee825dc971c544b5b 0.08477148889370165 seconds
da0a9f8e66696a4c6683055bc22c7378b7430041 0.08885913200959392 seconds
e5ae3c3fcd1f414dea2be83e0564f09fe3365ea9 0.08390960488084279 seconds
```
Using `--exec` actions and some python-fu, `asvdb` itself can even show the regressions:
```
user@machine> asvdb --read-from=./my_asv_dir \
  --exec-once="regressions=[]; prev=0" \
  --filter="funcName=='bench_algos.bench_pagerank_time' \
      and argNameValuePairs==[('dataset', '../datasets/csv/directed/cit-Patents.csv'), ('managed_mem', 'False'), ('pool_allocator', 'True')]" \
  --exec="t=prev; prev=result; d=result-t; regressions=regressions+[(commitHash, d)] if d>0.0001 else regressions" \
  --exec-once="print('Regressions:\n'+'\n'.join([f'commit: {r[0]} delta: {r[1]}' for r in regressions[1:]]))"

Regressions:
commit: 8f077b8700cc5d1b4632c429557eaed6057e03a1 delta: 0.00031180360821349284
commit: da0a9f8e66696a4c6683055bc22c7378b7430041 delta: 0.00408764311589227
```
_Note: since `asvdb` reads and writes databases that are (obviously) compatible with [airspeed velocity (ASV)](https://github.com/airspeed-velocity/asv), the `asv` CLI is another excellent option for finding regressions from the command line, as described [here](https://asv.readthedocs.io/en/stable/commands.html#asv-compare)_

- Get the requirements (dependencies) used for a specific commit
```
user@machine> asvdb --read-from=./my_asv_dir \
  --filter="commitHash=='c29c3e359d1d945ef32b6867809a331f460d3e46'" \
  --print="requirements"|sort -u

{'cudf': '0.14.200528', 'packageA': '0.0.6', 'packageB': '0.9.5'}
```
Even though this is limiting the rows to just one commit (by using the `--filter` action), there are still several results from the various runs done on that commit, hence the `sort -u`

- Change the unit string for specific benchmarks. This example first prints the current unit (seconds), then changes it to milliseconds, then prints it again to confirm the change:
```
user@machine> asvdb --read-from=./my_asv_dir \
  --filter="funcName=='bench_algos.bench_pagerank_time'" \
  --print=unit|sort -u

seconds

user@machine> asvdb --read-from=./my_asv_dir \
  --filter="funcName=='bench_algos.bench_pagerank_time'" \
  --exec="unit='milliseconds'" \
  --write-to=./my_asv_dir

user@machine> asvdb --read-from=./my_asv_dir \
  --filter="funcName=='bench_algos.bench_pagerank_time'" \
  --print=unit|sort -u

milliseconds
```
_Note: changing the unit to `milliseconds` here is just to illustrate how `asvdb` can update the database. Not all reporting tools that read from the database may recognize different unit strings._

- Change an individual result in the database, in this case, the latest result for the `pagerank_gpumem` benchmark that was run on `ubuntu-16.04`, python `3.6`, CUDA `10.1`, with a specific arg combination. This example uses individual `--filter` actions to reduce the rows down to the a single row so the `--exec` applies to only one, then it writes the row back to the same database it read from:
```
user@machine> asvdb --read-from=cugraph-e2e \
  --exec-once="latest=0" \
  --exec="latest=max(latest, commitTime)" \
  \
  --filter="commitTime==latest" \
  --filter="osType=='ubuntu-16.04'" \
  --filter="pythonVer=='3.6'" \
  --filter="cudaVer=='10.1'" \
  --filter="funcName=='bench_algos.bench_pagerank_gpumem'" \
  --filter="argNameValuePairs==[('dataset', '../datasets/csv/undirected/hollywood.csv'), ('managed_mem', 'True'), ('pool_allocator', 'True')]" \
  \
  --print="'Modifying result for:', commitHash, funcName, osType, pythonVer, cudaVer" \
  \
  --exec="result=0" \
  \
  --write-to=cugraph-e2e

Modifying result for: e630ffb768af8af95d189ba5775ce6dad38476a2 bench_algos.bench_pagerank_gpumem ubuntu-16.04 3.6 10.1
```
The initial `--exec-once` and `--exec` actions find the latest commit for all rows and save it to a new variable named `latest`, which is then used in a later `--filter` action. The individual `--filter` actions make the command much easier to read, but are less efficient that combining them into a single filter expression. This is because each `--filter` action is applied to each row, and the resulting filtered list of rows are then passed to the next action to run on each resulting row again. Instead, the `--filter` expressions could be combined into a single but harder-to-read expression that only makes a single pass through all the rows:
```
asvdb --read-from=cugraph-e2e --exec-once="latest=0" --exec="latest=max(latest, commitTime)" --filter="osType=='ubuntu-16.04' and pythonVer=='3.6' and cudaVer=='10.1' and commitTime==latest and funcName=='bench_algos.bench_pagerank_gpumem' and argNameValuePairs==[('dataset', '../datasets/csv/undirected/hollywood.csv'), ('managed_mem', 'True'), ('pool_allocator', 'True')]" --print="'Modifying result for:', commitHash, funcName, osType, pythonVer, cudaVer" --exec="result=0" --write-to=cugraph-e2e

Modifying result for: e630ffb768af8af95d189ba5775ce6dad38476a2 bench_algos.bench_pagerank_gpumem ubuntu-16.04 3.6 10.1
```
FWIW, the performance impact of the former is probably negligible and worth the improved readability/maintainability. For instance, on my system when using the `time` command for both examples, there was only a 0.124 second difference.

- Read an existing database and create a new database containing only the latest commit from branch-0.14 and branch-0.15
```
user@machine> asvdb --read-from=./my_asv_dir \
  --print="commitTime, branch, commitHash"|sort -u

1591733122000 branch-0.14 da0a9f8e66696a4c6683055bc22c7378b7430041
1591733228000 branch-0.14 e5ae3c3fcd1f414dea2be83e0564f09fe3365ea9
1591733272000 branch-0.15 ff154939008654e62b6696cee825dc971c544b5b
1591733292000 branch-0.14 c29c3e359d1d945ef32b6867809a331f460d3e46
1591738722000 branch-0.15 8f077b8700cc5d1b4632c429557eaed6057e03a1

user@machine> asvdb --read-from=./my_asv_dir \
  --exec-once="latest={}" \
  --exec="latest[branch]=max(commitTime, latest.get(branch,0))" \
  \
  --filter="branch in ['branch-0.14', 'branch-0.15'] and commitTime==latest[branch]" \
  \
  --write-to=./new_asv_dir

user@machine> asvdb --read-from=./new_asv_dir \
  --print="commitTime, branch, commitHash"|sort -u

1591733292000 branch-0.14 c29c3e359d1d945ef32b6867809a331f460d3e46
1591738722000 branch-0.15 8f077b8700cc5d1b4632c429557eaed6057e03a1
```
In the above example, an existing database is read from and a new database is written to using only the latest commits for `branch-0.14` and `branch-0.15` from the existing db.  This is done using several actions chained together:
1) initialize a dict named `latest` used to hold the latest `commitTime` for each `branch`
2) evaluate each row to update `latest` for the row's `branch` with the `commitTime` of the (potentially) higher time value
3) filter the rows to include only branches that are `branch-0.14` or `branch-0.15` **and** have the latest `commitTime`
4) finally, write the resulting rows to the new database.


### `asvdb` Python library - Read results from the "database"
```
>>> import asvdb
>>> db = asvdb.ASVDb("/path/to/benchmarks/asv")
>>>
>>> results = db.getResults()  # Get a list of (BenchmarkInfo obj, [BenchmarkResult obj, ...]) tuples.
>>> len(results)
9
>>> firstResult = results[0]
>>> firstResult[0]
BenchmarkInfo(machineName='my_machine', cudaVer='9.2', osType='debian', pythonVer='3.6', commitHash='f6242e77bf32ed12c78ddb3f9a06321b2fd11806', commitTime=1589322352000, gpuType='Tesla V100-SXM2-32GB', cpuType='x86_64', arch='x86_64', ram='540954406912')
>>> len(firstResult[1])
132
>>> firstResult[1][0]
BenchmarkResult(funcName='bench_algos.bench_create_edgelist_time', result=0.46636209040880205, argNameValuePairs=[('csvFileName', '../datasets/csv/undirected/hollywood.csv')], unit='seconds')
>>>
```

### `asvdb` Python library - Add benchmark results to the "database"
```
import platform
import psutil
from asvdb import utils, BenchmarkInfo, BenchmarkResult, ASVDb

# Create a BenchmarkInfo object describing the benchmarking environment.
# This can/should be reused when adding multiple results from the same environment.

uname = platform.uname()
(commitHash, commitTime) = utils.getCommitInfo()  # gets commit info from CWD by default

bInfo = BenchmarkInfo(machineName=uname.machine,
                      cudaVer="10.0",
                      osType="%s %s" % (uname.system, uname.release),
                      pythonVer=platform.python_version(),
                      commitHash=commitHash,
                      commitTime=commitTime,
                      gpuType="n/a",
                      cpuType=uname.processor,
                      arch=uname.machine,
                      ram="%d" % psutil.virtual_memory().total)

# Create result objects for each benchmark result. Each result object
# represents a result from a single benchmark run, including any specific
# parameter settings the benchmark used (ie. arg values to a benchmark function)
bResult1 = BenchmarkResult(funcName="myAlgoBenchmarkFunc",
                           argNameValuePairs=[
                              ("iterations", 100),
                              ("dataset", "januaryData")
                           ],
                           result=301.23)

bResult2 = BenchmarkResult(funcName="myAlgoBenchmarkFunc",
                           argNameValuePairs=[
                              ("iterations", 100),
                              ("dataset", "februaryData")
                           ],
                           result=287.93)

# Create an interface to an ASV "database" to write the results to.
(repo, branch) = utils.getRepoInfo()  # gets repo info from CWD by default

db = ASVDb(dbDir="/datasets/benchmarks/asv",
           repo=repo,
           branches=[branch])

# Each addResult() call adds the result and creates/updates all JSON files
db.addResult(bInfo, bResult1)
db.addResult(bInfo, bResult2)
```
This results in a `asv.conf.json` file in `/datasets/benchmarks/asv` containing:
```
{
  "results_dir": "results",
  "html_dir": "html",
  "repo": <the repo URL>,
  "branches": [
    <the branch name>
  ],
  "version": 1.0
}
```
and `results/benchmarks.json` containing:
```
{
  "myAlgoBenchmarkFunc": {
    "code": "myAlgoBenchmarkFunc",
    "name": "myAlgoBenchmarkFunc",
    "param_names": [
      "iterations",
      "dataset"
    ],
    "params": [
      [
        100,
        100
      ],
      [
        "januaryData",
        "februaryData"
      ]
    ],
    "timeout": 60,
    "type": "time",
    "unit": "seconds",
    "version": 2
  },
  "version": 2
}
```
a `<machine>/machine.json` file containing:
```
{
  "arch": "x86_64",
  "cpu": "x86_64",
  "gpu": "n/a",
  "cuda": "10.0",
  "machine": "x86_64",
  "os": "Linux 4.4.0-146-generic",
  "ram": "540955688960",
  "version": 1
}
```
and a `<machine>/<commit hash>.json` file containing:
```
{
  "params": {
    "gpu": "n/a",
    "cuda": "10.0",
    "machine": "x86_64",
    "os": "Linux 4.4.0-146-generic",
    "python": "3.7.1"
  },
  "requirements": {},
  "results": {
    "myAlgoBenchmarkFunc": {
      "params": [
        [
          100,
          100
        ],
        [
          "januaryData",
          "februaryData"
        ]
      ],
      "result": [
        301.23,
        287.93
      ]
    }
  },
  "commit_hash": "c551640ca829c32f520771306acc2d177398b721",
  "date": "156812889600",
  "python": "3.7.1",
  "version": 1
}
```
