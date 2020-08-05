from os import path
import os
import tempfile
import json
import threading
import time

import pytest
import boto3

datasetName = "dolphins.csv"
algoRunResults = [('loadDataFile', 3.2228727098554373),
                  ('createGraph', 3.00713360495865345),
                  ('pagerank', 3.00899268127977848),
                  ('bfs', 3.004273353144526482),
                  ('sssp', 3.004624705761671066),
                  ('jaccard', 3.0025573652237653732),
                  ('louvain', 3.32631026208400726),
                  ('weakly_connected_components', 3.0034315641969442368),
                  ('overlap', 3.002147899940609932),
                  ('triangles', 3.2544921860098839),
                  ('spectralBalancedCutClustering', 3.03329935669898987),
                  ('spectralModularityMaximizationClustering', 3.011258183047175407),
                  ('renumber', 3.001620553433895111),
                  ('view_adj_list', 3.000927431508898735),
                  ('degree', 3.0016251634806394577),
                  ('degrees', None)]
repo = "myrepo"
branch = "my_branch"
commitHash = "809a1569e8a2ff138cdde4d9c282328be9dcad43"
commitTime = 1590007324
machineName = "my_machine"


def createAndPopulateASVDb(dbDir):
    from asvdb import ASVDb, BenchmarkInfo

    db = ASVDb(dbDir, repo, [branch])
    bInfo = BenchmarkInfo(machineName=machineName,
                          cudaVer="9.2",
                          osType="linux",
                          pythonVer="3.6",
                          commitHash=commitHash,
                          commitTime=commitTime,
                          branch=branch,
                          gpuType="n/a",
                          cpuType="x86_64",
                          arch="my_arch",
                          ram="123456")

    return addResultsForInfo(db, bInfo)


def addResultsForInfo(db, bInfo):
    from asvdb import ASVDb, BenchmarkResult

    for (algoName, exeTime) in algoRunResults:
        bResult = BenchmarkResult(funcName=algoName,
                                  argNameValuePairs=[("dataset", datasetName)],
                                  result=exeTime)
        db.addResult(bInfo, bResult)

    return db


def test_addResult():
    asvDir = tempfile.TemporaryDirectory()
    db = createAndPopulateASVDb(asvDir.name)
    asvDir.cleanup()


def test_addResults():
    asvDir = tempfile.TemporaryDirectory()
    from asvdb import ASVDb, BenchmarkInfo, BenchmarkResult

    dbDir = asvDir.name
    db = ASVDb(dbDir, repo, [branch])
    bInfo = BenchmarkInfo(machineName=machineName,
                          cudaVer="9.2",
                          osType="linux",
                          pythonVer="3.6",
                          commitHash=commitHash,
                          commitTime=commitTime,
                          branch=branch,
                          gpuType="n/a",
                          cpuType="x86_64",
                          arch="my_arch",
                          ram="123456")

    resultList = []
    for (algoName, exeTime) in algoRunResults:
        bResult = BenchmarkResult(funcName=algoName,
                                  argNameValuePairs=[("dataset", datasetName)],
                                  result=exeTime)
        resultList.append(bResult)

    db.addResults(bInfo, resultList)

    # read back in and check
    dbCheck = ASVDb(dbDir, repo, [branch])
    retList = dbCheck.getResults()
    assert len(retList) == 1
    assert retList[0][0] == bInfo
    assert len(retList[0][1]) == len(algoRunResults)
    assert resultList == retList[0][1]

    asvDir.cleanup()


def test_writeWithoutRepoSet():
    from asvdb import ASVDb

    tmpDir = tempfile.TemporaryDirectory()
    asvDirName = path.join(tmpDir.name, "dir_that_does_not_exist")

    db1 = ASVDb(asvDirName)
    with pytest.raises(AttributeError):
        db1.updateConfFile()


def test_asvDirDNE():
    from asvdb import ASVDb

    tmpDir = tempfile.TemporaryDirectory()
    asvDirName = path.join(tmpDir.name, "dir_that_does_not_exist")
    repo = "somerepo"
    branch1 = "branch1"

    db1 = ASVDb(asvDirName, repo, [branch1])
    db1.updateConfFile()

    confFile = path.join(asvDirName, "asv.conf.json")
    with open(confFile) as fobj:
        j = json.load(fobj)
        branches = j["branches"]

    assert branches == [branch1]

    tmpDir.cleanup()


def test_newBranch():
    from asvdb import ASVDb

    asvDir = tempfile.TemporaryDirectory()
    repo = "somerepo"
    branch1 = "branch1"
    branch2 = "branch2"

    db1 = ASVDb(asvDir.name, repo, [branch1])
    db1.updateConfFile()
    db2 = ASVDb(asvDir.name, repo, [branch2])
    db2.updateConfFile()

    confFile = path.join(asvDir.name, "asv.conf.json")
    with open(confFile) as fobj:
        j = json.load(fobj)
        branches = j["branches"]

    assert branches == [branch1, branch2]

    asvDir.cleanup()


def test_gitExtension():
    from asvdb import ASVDb

    asvDir = tempfile.TemporaryDirectory()
    repo = "somerepo"
    branch1 = "branch1"

    db1 = ASVDb(asvDir.name, repo, [branch1])
    db1.updateConfFile()

    confFile = path.join(asvDir.name, "asv.conf.json")
    with open(confFile) as fobj:
        j = json.load(fobj)
        repo = j["repo"]

    assert repo.endswith(".git")

    asvDir.cleanup()


def test_concurrency():
    from asvdb import ASVDb, BenchmarkInfo, BenchmarkResult

    tmpDir = tempfile.TemporaryDirectory()
    asvDirName = path.join(tmpDir.name, "dir_that_does_not_exist")
    repo = "somerepo"
    branch1 = "branch1"

    db1 = ASVDb(asvDirName, repo, [branch1])
    db2 = ASVDb(asvDirName, repo, [branch1])
    db3 = ASVDb(asvDirName, repo, [branch1])
    # Use the writeDelay member var to insert a delay during write to properly
    # test collisions by making writes slow.
    db1.writeDelay = 10
    db2.writeDelay = 10

    bInfo = BenchmarkInfo()
    bResult1 = BenchmarkResult(funcName="somebenchmark1", result=43)
    bResult2 = BenchmarkResult(funcName="somebenchmark2", result=43)
    bResult3 = BenchmarkResult(funcName="somebenchmark3", result=43)

    # db1 or db2 should be actively writing the result (because the writeDelay is long)
    # and db3 should be blocked.
    t1 = threading.Thread(target=db1.addResult, args=(bInfo, bResult1))
    t2 = threading.Thread(target=db2.addResult, args=(bInfo, bResult2))
    t3 = threading.Thread(target=db3.addResult, args=(bInfo, bResult3))
    t1.start()
    t2.start()
    time.sleep(0.5)  # ensure t3 tries to write last
    t3.start()

    # Check that db3 is blocked - if locking wasn't working, it would have
    # finished since it has no writeDelay.
    t3.join(timeout=0.5)
    assert t3.is_alive() is True

    # Cancel db1 and db2, allowing db3 to write and finish
    db1.cancelWrite = True
    db2.cancelWrite = True
    t3.join(timeout=11)
    assert t3.is_alive() is False
    t1.join()
    t2.join()
    t3.join()

    # Check that db3 wrote its result
    with open(path.join(asvDirName, "results", "benchmarks.json")) as fobj:
        jo = json.load(fobj)
        assert "somebenchmark3" in jo
        #print(jo)

    tmpDir.cleanup()

def test_concurrency_stress():
    from asvdb import ASVDb, BenchmarkInfo, BenchmarkResult

    tmpDir = tempfile.TemporaryDirectory()
    asvDirName = path.join(tmpDir.name, "dir_that_does_not_exist")
    repo = "somerepo"
    branch1 = "branch1"
    num = 32
    dbs = []
    threads = []
    allFuncNames = []

    bInfo = BenchmarkInfo(machineName=machineName)

    for i in range(num):
        db = ASVDb(asvDirName, repo, [branch1])
        db.writeDelay=0.5
        dbs.append(db)

        funcName = f"somebenchmark{i}"
        bResult = BenchmarkResult(funcName=funcName, result=43)
        allFuncNames.append(funcName)

        t = threading.Thread(target=db.addResult, args=(bInfo, bResult))
        threads.append(t)

    for i in range(num):
        threads[i].start()

    for i in range(num):
        threads[i].join()

    # There should be num unique results in the db after (re)reading.  Pick any
    # of the db instances to read, they should all see the same results.
    results = dbs[0].getResults()
    assert len(results[0][1]) == num

    # Simply check that all unique func names were read back in.
    allFuncNamesCheck = [r.funcName for r in results[0][1]]
    assert sorted(allFuncNames) == sorted(allFuncNamesCheck)

    tmpDir.cleanup()


def test_s3_concurrency():
    from asvdb import ASVDb, BenchmarkInfo, BenchmarkResult

    tmpDir = tempfile.TemporaryDirectory(suffix='asv')
    asvDirName = "s3://gpuci-cache-testing/asvdb"
    resource = boto3.resource('s3')
    bucketName = "gpuci-cache-testing"
    benchmarkKey = "asvdb/results/benchmarks.json"
    repo = "somerepo"
    branch1 = "branch1"

    db1 = ASVDb(asvDirName, repo, [branch1])
    db2 = ASVDb(asvDirName, repo, [branch1])
    db3 = ASVDb(asvDirName, repo, [branch1])
    # Use the writeDelay member var to insert a delay during write to properly
    # test collisions by making writes slow.
    db1.writeDelay = 10
    db2.writeDelay = 10

    bInfo = BenchmarkInfo()
    bResult1 = BenchmarkResult(funcName="somebenchmark1", result=43)
    bResult2 = BenchmarkResult(funcName="somebenchmark2", result=43)
    bResult3 = BenchmarkResult(funcName="somebenchmark3", result=43)

    # db1 or db2 should be actively writing the result (because the writeDelay is long)
    # and db3 should be blocked.
    t1 = threading.Thread(target=db1.addResult, args=(bInfo, bResult1))
    t2 = threading.Thread(target=db2.addResult, args=(bInfo, bResult2))
    t3 = threading.Thread(target=db3.addResult, args=(bInfo, bResult3))
    t1.start()
    t2.start()
    time.sleep(0.5)  # ensure t3 tries to write last
    t3.start()

    # Check that db3 is blocked - if locking wasn't working, it would have
    # finished since it has no writeDelay.
    t3.join(timeout=0.5)
    assert t3.is_alive() is True

    # Cancel db1 and db2, allowing db3 to write and finish
    db1.cancelWrite = True
    db2.cancelWrite = True
    t3.join(timeout=11)
    assert t3.is_alive() is False
    t1.join()
    t2.join()
    t3.join()

    # Check that db3 wrote its result
    os.makedirs(path.join(tmpDir.name, "asvdb/results"))
    resource.Bucket(bucketName).download_file(benchmarkKey, path.join(tmpDir.name, benchmarkKey))
    with open(path.join(tmpDir.name, benchmarkKey)) as fobj:
        jo = json.load(fobj)
        assert "somebenchmark3" in jo

    tmpDir.cleanup()
    db3.s3Resource.Bucket(db3.bucketName).objects.filter(Prefix="asvdb/").delete()


def test_s3_concurrency_stress():
    from asvdb import ASVDb, BenchmarkInfo, BenchmarkResult

    asvDirName = "s3://gpuci-cache-testing/asvdb"
    bucketName = "gpuci-cache-testing"
    repo = "somerepo"
    branch1 = "branch1"
    num = 32
    dbs = []
    threads = []
    allFuncNames = []

    bInfo = BenchmarkInfo(machineName=machineName)

    for i in range(num):
        db = ASVDb(asvDirName, repo, [branch1])
        db.writeDelay=0.5
        dbs.append(db)

        funcName = f"somebenchmark{i}"
        bResult = BenchmarkResult(funcName=funcName, result=43)
        allFuncNames.append(funcName)

        t = threading.Thread(target=db.addResult, args=(bInfo, bResult))
        threads.append(t)

    for i in range(num):
        threads[i].start()

    for i in range(num):
        threads[i].join()

    # There should be num unique results in the db after (re)reading.  Pick any
    # of the db instances to read, they should all see the same results.
    results = dbs[0].getResults()
    assert len(results[0][1]) == num

    # Simply check that all unique func names were read back in.
    allFuncNamesCheck = [r.funcName for r in results[0][1]]
    assert sorted(allFuncNames) == sorted(allFuncNamesCheck)

    db3.s3Resource.Bucket(db3.bucketName).objects.filter(Prefix="asv/").delete()



def test_read():
    from asvdb import ASVDb

    tmpDir = tempfile.TemporaryDirectory()
    asvDirName = path.join(tmpDir.name, "dir_that_did_not_exist_before")
    createAndPopulateASVDb(asvDirName)

    db1 = ASVDb(asvDirName)
    db1.loadConfFile()
    # asvdb always ensures repos end in .git
    assert db1.repo == f"{repo}.git"
    assert db1.branches == [branch]

    # getInfo() returns a list of BenchmarkInfo objs
    biList = db1.getInfo()
    assert len(biList) == 1
    bi = biList[0]
    assert bi.machineName == machineName
    assert bi.commitHash == commitHash
    assert bi.commitTime == commitTime
    assert bi.branch == branch

    # getResults() returns a list of tuples:
    # (BenchmarkInfo obj, [BenchmarkResult obj, ...])
    brList = db1.getResults()
    assert len(brList) == len(biList)
    assert brList[0][0] == bi
    results = brList[0][1]
    assert len(results) == len(algoRunResults)
    br = results[0]
    assert br.funcName == algoRunResults[0][0]
    assert br.argNameValuePairs == [("dataset", datasetName)]
    assert br.result == algoRunResults[0][1]


def test_getFilteredResults():
    from asvdb import ASVDb, BenchmarkInfo

    tmpDir = tempfile.TemporaryDirectory()
    asvDirName = path.join(tmpDir.name, "dir_that_did_not_exist_before")

    db = ASVDb(asvDirName, repo, [branch])
    bInfo1 = BenchmarkInfo(machineName=machineName,
                           cudaVer="9.2",
                           osType="linux",
                           pythonVer="3.6",
                           commitHash=commitHash,
                           commitTime=commitTime)
    bInfo2 = BenchmarkInfo(machineName=machineName,
                           cudaVer="10.1",
                           osType="linux",
                           pythonVer="3.7",
                           commitHash=commitHash,
                           commitTime=commitTime)
    bInfo3 = BenchmarkInfo(machineName=machineName,
                           cudaVer="10.0",
                           osType="linux",
                           pythonVer="3.7",
                           commitHash=commitHash,
                           commitTime=commitTime)

    addResultsForInfo(db, bInfo1)
    addResultsForInfo(db, bInfo2)
    addResultsForInfo(db, bInfo3)

    # should only return results associated with bInfo1
    brList1 = db.getResults(filterInfoObjList=[bInfo1])
    assert len(brList1) == 1
    assert brList1[0][0] == bInfo1
    assert len(brList1[0][1]) == len(algoRunResults)

    # should only return results associated with bInfo1 or bInfo3
    brList1 = db.getResults(filterInfoObjList=[bInfo1, bInfo3])
    assert len(brList1) == 2
    assert brList1[0][0] in [bInfo1, bInfo3]
    assert brList1[1][0] in [bInfo1, bInfo3]
    assert brList1[0][0] != brList1[1][0]
    assert len(brList1[0][1]) == len(algoRunResults)
    assert len(brList1[1][1]) == len(algoRunResults)
    
