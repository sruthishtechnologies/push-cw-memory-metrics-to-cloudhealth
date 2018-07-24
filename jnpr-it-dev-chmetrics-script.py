import boto3
import datetime
import json
from dateutil.tz import tzutc
import requests
import logging
import time

#Variables to specify the AWS regions to execute script in specified regions, AWS Account Number, AWS credentials profile name, cloud health API key
regions = ['us-east-1','us-west-1','us-west-2','eu-west-1','sa-east-1','ap-southeast-1','ap-southeast-2','ap-northeast-1']
aws_acc_no = ''
aws_profile = ''
cloudhealth_key = ""

today = datetime.date.today()
yesterday = today - datetime.timedelta(days = 1)
yy = yesterday.year
ym = yesterday.month
yd = yesterday.day
ty = today.year
tm = today.month
td = today.day

boto3.setup_default_session(profile_name=aws_profile)

#Below code block will help to get memory metrics from cloud watch 
def get_memory_metrics(region,InstanceId, parms):
	#print "Get Metrics"
	#boto3.setup_default_session(profile_name=aws_profile)
	cw = boto3.client('cloudwatch',region_name=region)
	response = cw.get_metric_statistics(
		Namespace= parms['name_space'],
		MetricName= parms['metric_name'],
		Dimensions=[{'Name': parms['Instance'],'Value': InstanceId},],
		#StartTime=datetime.datetime(yesterday.year, yesterday.month, yesterday.day),
		StartTime=datetime.datetime(yy, ym, yd),
		#EndTime=datetime.datetime(today.year, today.month, today.day),
		EndTime=datetime.datetime(ty, tm, td),
		Period=3600,
		Statistics=['Average', 'Minimum', 'Maximum']	
		)
	#print response
	return response


#This block is to get list of all Cloud Watch metrics
def get_list_metrics(region):
	filtermetrics = ['MemoryUtilization','UsedMemoryPCT','FreeMemory']
	boto3.setup_default_session(profile_name=aws_profile)
	cw = boto3.client('cloudwatch',region_name=region)
	paginator = cw.get_paginator('list_metrics')
	page_iterator = paginator.paginate(PaginationConfig={'MaxItems': 100000})
	for page in page_iterator:
		for item in page['Metrics']:
			parms ={}
			#print item
			if item['MetricName'] in filtermetrics:
				print "======="
				print "NameSpace : "+item['Namespace']
				parms["name_space"] = item["Namespace"]
				print "MetricName : "+item['MetricName']
				parms["metric_name"] = item["MetricName"]
				#print parms
				for value in item['Dimensions']:
					if value['Name'] == 'InstanceId' or 'Instanceid':
						print value['Value']
						parms['Instance'] = value["Name"]
						parms['inst_id'] = value["Value"]
						print parms
						metricsdata = get_memory_metrics(region,value['Value'], parms)
						valuessets = []
						instance_arn = region+":"+aws_acc_no+":"+parms['inst_id']
						print instance_arn
						for dp in metricsdata['Datapoints']:
							#print dp
							Timestamp = dp['Timestamp'].isoformat()
							valuesset = "[\""+instance_arn+'","'+Timestamp+'",'+str(dp['Average'])+','+str(dp['Maximum'])+','+str(dp['Minimum'])+']'
							valuessets.append(valuesset)
							#prepare_data(region,parms,dp)
							#time.sleep(2)
						print "++++++++++"
						print valuessets
						valuessetsnew = str(valuessets)
						pushdata = valuessetsnew.replace("'","")
						#print type(valuessetsnew)
						print '++++++++++'
						prepare_data(region,parms,pushdata)
						
						print "------"
	#print "======"

#This block will prepare the data format to push
def prepare_data(region,parms,valuessets):
	print "preparing data"
	dataformat = ''
	metadataformat = ''
	#Timestamp = dp['Timestamp'].isoformat()
	#instance_arn = region+":"+aws_acc_no+":"+parms['inst_id']
	#print instance_arn

	if parms['metric_name'] == 'FreeMemory':
		print "FreeMemory details"
		metadataformat ='{"metrics":{"datasets":[{"metadata":{"assetType":"aws:ec2:instance","granularity":"hour","keys":["assetId","timestamp","memory:free:bytes.avg","memory:free:bytes.max","memory:free:bytes.min"]},"values":'+str(valuessets)+'}]}}'
	else:
		print "Non FreeMemory"
		metadataformat ='{"metrics":{"datasets":[{"metadata":{"assetType":"aws:ec2:instance","granularity":"hour","keys":["assetId","timestamp","memory:usedPercent.avg","memory:usedPercent.max","memory:usedPercent.min"]},"values":'+str(valuessets)+'}]}}'

	#valuesset = '["'+instance_arn+'","'+Timestamp+'",'+str(dp['Average'])+','+str(dp['Maximum'])+','+str(dp['Minimum'])+']'
	#metadataformat = metadataformat+valuesset
	print metadataformat
	push_data_to_ch(metadataformat)


#This code will push the metrics to cloud health
def push_data_to_ch(payload):
	#print payload
	payload = payload
	print "pushing data to cloud health"
	url = "https://chapi.cloudhealthtech.com/metrics/v1"
	querystring = {"api_key": cloudhealth_key}
	headers = {
	'accept': "application/json",
	'content-type': "application/json",
	'cache-control': "no-cache",
	'postman-token': "e5beff53-f6e3-d095-d620-bcba37bad257"
	}
	response = requests.request("POST", url, data=payload, headers=headers, params=querystring)
	print response.status_code, response.reason
	print(response.text)

def main():
	st = datetime.datetime.now()
	for region in regions:
		filtermetrics = ['MemoryUtilization','UsedMemoryPCT','FreeMemory']
		get_list_metrics(region)
	et = datetime.datetime.now()
	print "Script Starting time : ",st
	print "Script Ending time   : ",et
	tt = et - st
	print "Total script runing time : ",tt


if __name__ == '__main__':
	main()
