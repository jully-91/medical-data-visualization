from utils.getPublicData import getAllCasesData


def getPieData():
    casesList = getAllCasesData()
    ageDic = {'0-10岁':0,'10-20岁':0,'10-20岁':0,'20-30岁':0,'30-40岁':0,'40-50岁':0,'50-60岁':0,'60岁以上':0}
    for caseItem in casesList:
        if int(caseItem[3]) < 10:
            ageDic['0-10岁'] += 1
        elif int(caseItem[3]) < 20:
            ageDic['10-20岁'] += 1
        elif int(caseItem[3]) < 30:
            ageDic['20-30岁'] += 1
        elif int(caseItem[3]) < 40:
            ageDic['30-40岁'] += 1
        elif int(caseItem[3]) < 50:
            ageDic['40-50岁'] += 1
        elif int(caseItem[3]) < 60:
            ageDic['50-60岁'] += 1
        else:
            ageDic['60岁以上'] += 1
    # print(ageDic)
    listResult = []
    for k,v in ageDic.items():
        listResult.append({
            'name':k,
            'value':v
        })
    print(listResult)
    return listResult

def getConfigOne():
    casesList = getAllCasesData()
    caseDic = {}
    for caseItem in casesList:
        if caseDic.get(caseItem[1],-1) == -1:
            caseDic[caseItem[1]] = 1
        else:
            caseDic[caseItem[1]] += 1
    listResult = []
    for k,v in caseDic.items():
        listResult.append({
            'name':k,
            'value':v
        })
    print(1,listResult)
    return listResult[:6],listResult

def getFoundData():
    casesList = getAllCasesData()
    maxNum = len(list(casesList))
    typeDic = {}
    depDic = {}
    hosDic = {}
    maxAge = 0
    minAge = 100
    for caseItem in casesList:
        #类型
        if typeDic.get(caseItem[1],-1) == -1:
            typeDic[caseItem[1]] = 1
        else:
            typeDic[caseItem[1]] += 1
        #科室
        if depDic.get(caseItem[8],-1) == -1:
            depDic[caseItem[8]] = 1
        else:
            depDic[caseItem[8]] += 1
        #医院
        if hosDic.get(caseItem[7],-1) == -1:
            hosDic[caseItem[7]] = 1
        else:
            hosDic[caseItem[7]] += 1
        #年龄
        if int(caseItem[3]) > maxAge:
            maxAge = int(caseItem[3])
        if int(caseItem[3]) < minAge:
            minAge = int(caseItem[3])

    typeSort = sorted(typeDic.items(),key=lambda data:data[1],reverse=True)
    depSort = sorted(depDic.items(), key=lambda data: data[1], reverse=True)
    hosSort = sorted(hosDic.items(), key=lambda data: data[1], reverse=True)
    maxType = typeSort[0][0]
    maxDep = depSort[0][0]
    maxHos = hosSort[0][0]
    return maxNum,maxType,maxDep,maxHos,maxAge,minAge

def getGenderData():
    casesList = getAllCasesData()
    boyDic = {}
    girlDic = {}
    boyNum = 0
    girlNum = 0
    for caseItem in casesList:
        if caseItem[2] == '男':
            boyNum += 1
            if boyDic.get(caseItem[1],-1) == -1:
                boyDic[caseItem[1]] = 1
            else:
                boyDic[caseItem[1]] += 1
        elif caseItem[2] == '女':
            girlNum += 1
            if girlDic.get(caseItem[1],-1) == -1:
                girlDic[caseItem[1]] = 1
            else:
                girlDic[caseItem[1]] += 1

    ratioData = []
    boyRatio = int(round(boyNum / len(casesList) * 100,0))
    girlRatio = int(round(girlNum / len(casesList) * 100,0))
    print(boyRatio, girlRatio)
    ratioData.append(girlRatio)
    ratioData.append(boyRatio)
    boyList = []
    girlList = []
    for k,v in boyDic.items():
        boyList.append({
            'name':k,
            'value':v
        })
    for k,v in girlDic.items():
        girlList.append({
            'name':k,
            'value':v
        })
    return boyList,girlList,ratioData

def getCircleData():
    casesList = getAllCasesData()
    depDic = {}
    for caseItem in casesList:
        if depDic.get(caseItem[8],-1) == -1:
            depDic[caseItem[8]] = 1
        else:
            depDic[caseItem[8]] += 1
    # print(depDic)
    dataSort = sorted(depDic.items(),key=lambda data:data[1],reverse=True)
    dataResultList = []
    for i in dataSort:
        dataResultList.append({
            'name':i[0],
            'value':i[1]
        })

    return dataResultList

def getBodyData():
    casesList = getAllCasesData()
    dataDic = {}
    xData = []
    sumData = []
    for caseItem in casesList:
        if dataDic.get(caseItem[1],-1) == -1:
            dataDic[caseItem[1]] = 1
        else:
            dataDic[caseItem[1]] += 1
    dataSort = sorted(dataDic.items(),key=lambda data:data[1],reverse=True)
    for i in dataSort:
        xData.append(i[0])
        sumData.append(i[1])
    y1Data = [0 for x in range(len(xData))]
    y2Data = [0 for x in range(len(xData))]
    for caseItem in casesList:
        for index,x in enumerate(xData):
            if caseItem[1] == x:
                height = caseItem[10]
                weight = caseItem[11]
                if height in (None, '', '无') or weight in (None, '', '无'):
                    continue
                try:
                    y1Data[index] += int(height)
                    y2Data[index] += int(weight)
                except (ValueError, TypeError):
                    continue
    print(y1Data,y2Data,sumData)
    for index,sum in enumerate(sumData):
        y1Data[index] = round(y1Data[index]/sumData[index],0)
        y2Data[index] = round(y2Data[index] / sumData[index], 0)
    return xData,y1Data,y2Data
