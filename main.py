import math;
import random;
import os;
import sys;
import argparse;
import math;
import csv

#Some Constants
DROPPED_PACKET = 2
ERROR = 1
NO_ERROR = 0

#############################
#Clearing the timeout from eventList function
#in: original event list
#out: new event list
#############################
def clearTimeout(eventList):
	timeoutsList = []
	for i in eventList:
		if(i[0] == "Timeout"):
			timeoutsList.append(i)
	#Remove Timeout
	for i in timeoutsList:
		eventList.remove(i)

	return eventList


#############################
#Response ABP Function
#in: currentTime,sequence_number,Next_Expected_Frame_Receiver,BER,headerLength,total_size, tau, cRate
#out: response
#############################
def responseABP(currentTime,sequence_number,Next_Expected_Frame_Receiver,BER,headerLength,total_size, tau, cRate):
	#Calculate Percentages likelihood for Data Packet
	Pnoerror1 = (1-BER)**total_size
	Perror1 = 0
	numerator = total_size
	denominator = 1
	for i in range(1,5):
		Perror1 = Perror1 + ( (numerator/denominator) * (BER**i) * ((1-BER)**(total_size-i)) )
		denominator = denominator * (1 + i) 
		numerator = numerator * (total_size - i)
	Ploss1 = 1.0 - Pnoerror1 - Perror1


	#Calculate Percentages likelihood for Ack
	Pnoerror2 = (1-BER)**headerLength
	Perror2 = 0
	numerator = headerLength
	denominator = 1
	for i in range(1,5):
		Perror2 = Perror2 + ( (numerator/denominator) * (BER**i) * ((1-BER)**(headerLength-i)) )
		denominator = denominator * (i + 1) 
		numerator = numerator * (headerLength - i)
	Ploss2 = 1.0 - Pnoerror2 - Perror2

	randomChance = random.random()

	headerAckTime = headerLength/cRate


	if(randomChance <= Pnoerror1 ):
		#See if ACK Response will be corrupt
		randomChance = random.random()


		if(randomChance <= Pnoerror2):
			if(Next_Expected_Frame_Receiver == sequence_number):
				Next_Expected_Frame_Receiver = (Next_Expected_Frame_Receiver + 1)%2
				#return a successful ACK with correct sequence number
				return ["ACK", currentTime+(2*tau)+headerAckTime, NO_ERROR, Next_Expected_Frame_Receiver]
			else:
				#Return ACK with Wrong SN (Basically a NACK) because wrong next expected ack number
				return ["ACK", currentTime+(2*tau)+headerAckTime, ERROR, sequence_number]
		elif(randomChance >= Pnoerror2 + Perror2):
			#Return Nothing because ACK got dropped
			return 0
		else:
			#Return ACK with Wrong SN (Basically a NACK) because corrupted acknowledgement
			return ["ACK", currentTime+(2*tau)+headerAckTime, ERROR, sequence_number]
	
	elif(randomChance >= Pnoerror1 + Perror1):
		#Return Nothing because dropped data packet so nothing received
		return 0
		#return ["Dropped Packet", currentTime+tau, DROPPED_PACKET, sequence_number]
	
	else:
		#Return ACK with Wrong SN (Basically a NACK) because corrupted packet
		return ["ACK", currentTime+(2*tau)+headerAckTime, ERROR, sequence_number]


#############################
#ABP Function
#in: timeoutLength,BER,headerLength,packetLength,cRate,tau
#out: throughput
#############################
def ABP(timeoutLength,BER,headerLength,packetLength,cRate,tau):
	#Set up variables for throughput calculations
	currentTime = 0.0
	totalPacket = 0

	#Sequence Number either 1 or 0
	sequence_number = 0

	#total size
	total_size = headerLength + packetLength

	#The next expected ack
	Next_Expected_Ack_Sender = (sequence_number+1)%2
	Next_Expected_Frame_Receiver = 0

	#Event List
	eventList = []

	currentTime = total_size/cRate
	eventList.append(["Timeout", currentTime + timeoutLength, NO_ERROR, sequence_number])
	response = responseABP(currentTime,sequence_number,Next_Expected_Frame_Receiver,BER,headerLength,total_size, tau,cRate)

	#If Response isnt null (aka lost packet/ack)
	if(response):
		if(response[2] == NO_ERROR):
			Next_Expected_Frame_Receiver = (sequence_number + 1)%2
		eventList.append(response)
		eventList = sorted(eventList, key=lambda x: x[1], reverse=True);

	while(totalPacket < 10000):
		#Pop Next event in event list
		x = eventList.pop()

		if(x[0] == "Timeout"):
			#Resend Packet
			currentTime = x[1] + total_size/cRate
			eventList = clearTimeout(eventList)
			eventList.append(["Timeout", currentTime + timeoutLength, NO_ERROR, sequence_number])
			response = responseABP(currentTime,sequence_number,Next_Expected_Frame_Receiver,BER,headerLength,total_size, tau,cRate)

			#If Response isnt null (aka lost packet/ack)
			if(response):
				if(response[2] == NO_ERROR):
					Next_Expected_Frame_Receiver = (sequence_number + 1)%2
				eventList.append(response)
				eventList = sorted(eventList, key=lambda x: x[1], reverse=True);


		elif(x[0] == "ACK"):
			if(x[2] == NO_ERROR and Next_Expected_Ack_Sender == x[3]):
				totalPacket = totalPacket + 1
				if (totalPacket == 10000):
					break
				#Update seq number and expected seq num
				sequence_number = (sequence_number+1)%2
				Next_Expected_Ack_Sender = (sequence_number+1)%2

				eventList = clearTimeout(eventList)

				currentTime = x[1] + total_size/cRate

				eventList.append(["Timeout", currentTime + timeoutLength, NO_ERROR, sequence_number])
				response = responseABP(currentTime,sequence_number,Next_Expected_Frame_Receiver,BER,headerLength,total_size, tau,cRate)

				#If Response isnt null (aka lost packet/ack)
				if(response):
					if(response[2] == NO_ERROR):
						Next_Expected_Frame_Receiver = (sequence_number + 1)%2
					eventList.append(response)
					eventList = sorted(eventList, key=lambda x: x[1], reverse=True);

	return (totalPacket*packetLength/currentTime)


#############################
#ABP_NACK Function
#in: timeoutLength,BER,headerLength,packetLength,cRate,tau
#out: throughput
#############################
def ABP_NACK(timeoutLength,BER,headerLength,packetLength,cRate,tau):
	#Set up variables for throughput calculations
	currentTime = 0.0
	totalPacket = 0

	#Sequence Number either 1 or 0
	sequence_number = 0

	#total size
	total_size = headerLength + packetLength

	#The next expected ack
	Next_Expected_Ack_Sender = (sequence_number+1)%2
	Next_Expected_Frame_Receiver = 0

	#Event List
	eventList = []

	currentTime = total_size/cRate
	eventList.append(["Timeout", currentTime + timeoutLength, NO_ERROR, sequence_number])
	response = responseABP(currentTime,sequence_number,Next_Expected_Frame_Receiver,BER,headerLength,total_size, tau,cRate)

	#If Response isnt null (aka lost packet/ack)
	if(response):
		if(response[2] == NO_ERROR):
			Next_Expected_Frame_Receiver = (sequence_number + 1)%2
		eventList.append(response)
		eventList = sorted(eventList, key=lambda x: x[1], reverse=True);

	while(totalPacket < 10000):
		#Pop Next event in event list
		x = eventList.pop()

		if(x[0] == "Timeout"):
			#Resend Packet
			currentTime = x[1] + total_size/cRate
			eventList.append(["Timeout", currentTime + timeoutLength, NO_ERROR, sequence_number])
			response = responseABP(currentTime,sequence_number,Next_Expected_Frame_Receiver,BER,headerLength,total_size, tau,cRate)

			#If Response isnt null (aka lost packet/ack)
			if(response):
				#currentTime = response[1]
				if(response[2] == NO_ERROR):
					Next_Expected_Frame_Receiver = (sequence_number + 1)%2
				eventList.append(response)
				eventList = sorted(eventList, key=lambda x: x[1], reverse=True);


		elif(x[0] == "ACK"):
			if(x[2] == NO_ERROR and Next_Expected_Ack_Sender == x[3]):
				totalPacket = totalPacket + 1
				if (totalPacket == 10000):
					break
				#Update seq number and expected seq num
				sequence_number = (sequence_number+1)%2
				Next_Expected_Ack_Sender = (sequence_number+1)%2

				eventList = clearTimeout(eventList)

				currentTime = x[1] + total_size/cRate
				eventList.append(["Timeout", currentTime + timeoutLength, NO_ERROR, sequence_number])
				response = responseABP(currentTime,sequence_number,Next_Expected_Frame_Receiver,BER,headerLength,total_size, tau,cRate)

				#If Response isnt null (aka lost packet/ack)
				if(response):
					if(response[2] == NO_ERROR):
						Next_Expected_Frame_Receiver = (sequence_number + 1)%2
					eventList.append(response)
					eventList = sorted(eventList, key=lambda x: x[1], reverse=True);

			else:
				#Treat this as a NACK

				eventList = clearTimeout(eventList)

				#Resend Packet
				currentTime = x[1] + total_size/cRate
				eventList.append(["Timeout", currentTime + timeoutLength, NO_ERROR, sequence_number])
				response = responseABP(currentTime,sequence_number,Next_Expected_Frame_Receiver,BER,headerLength,total_size, tau,cRate)

				#If Response isnt null (aka lost packet/ack)
				if(response):
					if(response[2] == NO_ERROR):
						Next_Expected_Frame_Receiver = (sequence_number + 1)%2
					eventList.append(response)
					eventList = sorted(eventList, key=lambda x: x[1], reverse=True);

	return (totalPacket*packetLength/currentTime)


#############################
#Response GBN Function
#in: currentTime,sequence_number,Next_Expected_Frame_Receiver,BER,headerLength,total_size, tau, cRate
#out: response
#############################
def responseGBN(currentTime,sequence_number,Next_Expected_Frame_Receiver,BER,headerLength,total_size, tau, cRate):
	#Calculate Percentages likelihood for Data Packet
	Pnoerror1 = (1-BER)**total_size
	Perror1 = 0
	numerator = total_size
	denominator = 1
	for i in range(1,5):
		Perror1 = Perror1 + ( (numerator/denominator) * (BER**i) * ((1-BER)**(total_size-i)) )
		denominator = denominator * (1 + i) 
		numerator = numerator * (total_size - i)
	Ploss1 = 1.0 - Pnoerror1 - Perror1


	#Calculate Percentages likelihood for Ack
	Pnoerror2 = (1-BER)**headerLength
	Perror2 = 0
	numerator = headerLength
	denominator = 1
	for i in range(1,5):
		Perror2 = Perror2 + ( (numerator/denominator) * (BER**i) * ((1-BER)**(headerLength-i)) )
		denominator = denominator * (i + 1) 
		numerator = numerator * (headerLength - i)
	Ploss2 = 1.0 - Pnoerror2 - Perror2

	randomChance = random.random()

	headerAckTime = headerLength/cRate


	if(randomChance <= Pnoerror1 ):
		#See if ACK Response will be corrupt
		randomChance = random.random()


		if(randomChance <= Pnoerror2):
			if(Next_Expected_Frame_Receiver == sequence_number):
				Next_Expected_Frame_Receiver = (Next_Expected_Frame_Receiver + 1)%5
				#return a successful ACK with correct sequence number
				return ["ACK", currentTime+(2*tau)+headerAckTime, NO_ERROR, Next_Expected_Frame_Receiver]
			else:
				#Return ACK with Wrong SN (Basically a NACK) because wrong next expected ack number
				return ["ACK", currentTime+(2*tau)+headerAckTime, ERROR, sequence_number]
		elif(randomChance >= Pnoerror2 + Perror2):
			#Return Nothing because ACK got dropped
			return 0
		else:
			#Return ACK with Wrong SN (Basically a NACK) because corrupted acknowledgement
			return ["ACK", currentTime+(2*tau)+headerAckTime, ERROR, sequence_number]
	
	elif(randomChance >= Pnoerror1 + Perror1):
		#Return Nothing because dropped data packet so nothing received
		return 0
		#return ["Dropped Packet", currentTime+tau, DROPPED_PACKET, sequence_number]
	
	else:
		#Return ACK with Wrong SN (Basically a NACK) because corrupted packet
		return ["ACK", currentTime+(2*tau)+headerAckTime, ERROR, sequence_number]


#############################
#GBN Function
#in: timeoutLength,BER,headerLength,packetLength,cRate,tau
#out: throughput
#############################
def GBN(timeoutLength,BER,headerLength,packetLength,cRate,tau):
	#Set up variables for throughput calculations
	currentTime = 0.0
	totalPacket = 0

	#Packet info in buffer space
	#Index 0 is SN Index 1 is L Index 2 is T
	M = []

	#buffer size
	buffer_size = 4

	#Packets in Queue Count
	packetsCount = 0

	#total size
	total_size = headerLength + packetLength

	#The next expected ack
	#Next_Expected_Ack_Sender = 1
	Next_Expected_Frame_Receiver = 0

	#Event List
	eventList = []

	#P Value for sliding
	P = 0

	#Initial Buffer Setup
	M.append([0,total_size,total_size/cRate])
	M.append([1,total_size,2*total_size/cRate])
	M.append([2,total_size,3*total_size/cRate])
	M.append([3,total_size,4*total_size/cRate])

	#Send Initial Timeout
	eventList.append(["Timeout", currentTime + total_size/cRate + timeoutLength, NO_ERROR, M[0][0]])


	while(packetsCount < 4):
		currentTime = currentTime + total_size/cRate
		response = responseGBN(M[packetsCount][2],M[packetsCount][0],Next_Expected_Frame_Receiver,BER,headerLength,total_size, tau,cRate)

		#If Response isnt null (aka lost packet/ack)
		if(response):
			if(response[2] == NO_ERROR):
				Next_Expected_Frame_Receiver = response[3]
			eventList.append(response)
			eventList = sorted(eventList, key=lambda x: x[1], reverse=True);

		packetsCount = packetsCount + 1

	#currentTime = M[3][2]
		
	while(totalPacket < 10000):
		#Pop Next event in event list
		x = eventList.pop()

		while(currentTime <= x[1] and packetsCount < 4):
			currentTime = currentTime + total_size/cRate
			response = responseGBN(currentTime,M[packetsCount][0],Next_Expected_Frame_Receiver,BER,headerLength,total_size, tau,cRate)

			#If Response isnt null (aka lost packet/ack)
			if(response):
				if(response[2] == NO_ERROR):
					Next_Expected_Frame_Receiver = response[3]
				eventList.append(response)
				eventList = sorted(eventList, key=lambda x: x[1], reverse=True);

			packetsCount = packetsCount + 1

		if(x[0] == "Timeout"):

			#print "This should never happen"
			currentTime = x[1] + total_size/cRate

			eventList = clearTimeout(eventList)

			#Timed-out so now need to delete all events since I need to resend everything again
			eventList = []
			eventList.append(["Timeout", currentTime + timeoutLength, NO_ERROR, x[3]])
			
			#Update all Packet times in Queue
			M[0][2] = currentTime
			M[1][2] = M[0][2] + total_size/cRate
			M[2][2] = M[1][2] + total_size/cRate
			M[3][2] = M[2][2] + total_size/cRate
			

			Next_Expected_Frame_Receiver = M[0][0]
			P = M[0][0]
			response = responseGBN(currentTime,M[0][0],Next_Expected_Frame_Receiver,BER,headerLength,total_size, tau,cRate)
			packetsCount = 1

			#If Response isnt null (aka lost packet/ack)
			if(response):
				if(response[2] == NO_ERROR):
					Next_Expected_Frame_Receiver = response[3]
				eventList.append(response)
				eventList = sorted(eventList, key=lambda x: x[1], reverse=True);


		elif(x[0] == "ACK"):

			expectedNumbers = [(P+1)%5,(P+2)%5,(P+3)%5,(P+4)%5]
			if(x[2] == NO_ERROR and x[3] in expectedNumbers):
				totalPacket = totalPacket + 1
				if (totalPacket == 10000):
					break;

				slideCount = (x[3]-P)%5


				#Slide and Fill with new Packets
				for i in range(3,3+slideCount):
					if (i == 3):
						M.append([(M[i][0]+1)%5, total_size, x[1]+total_size/cRate])
					else:
						M.append([(M[i][0]+1)%5, total_size, M[i][2]+total_size/cRate])

				#Slice off all the ack'd packets
				M = M[slideCount:]


				eventList = clearTimeout(eventList)

				packetsCount = 4-slideCount

				P = M[0][0]


				eventList.append(["Timeout", M[0][2] + timeoutLength, NO_ERROR, M[0][0]])
				eventList = sorted(eventList, key=lambda x: x[1], reverse=True);
				
				currentTime = x[1]


	return (totalPacket*packetLength/currentTime)



#############################
#Main Function
#############################
def main():
	#BER, Tau and C
	BER = [0,0.00001,0.0001]
	tau = [0.005,0.25]
	C = 5000000.0

	#Header length H and Packet Length l
	H = 54.0*8
	L = 1500.0*8

	#Given Timeout Set
	timeoutSet = [2.5,5.0,7.5,10.0,12.5]

	#Final Result Array
	ABP_Result = []
	ABP_NACK_Result = []
	GBN_Result = []

	print "Loading..."

	mode = int(sys.argv[1])

	for i in timeoutSet:
		#Get Timeouts from Tau
		timeoutNumberOne = i*tau[0]
		timeoutNumberTwo = i*tau[1]

		if (mode == 1):
			#ABP Results
			temp_result = []
			for j in BER:
				temp_result.append(ABP(timeoutNumberOne,j,H,L,C,tau[0]))

			for j in BER:
				temp_result.append(ABP(timeoutNumberTwo,j,H,L,C,tau[1]))

			ABP_Result.append(temp_result)



		if (mode == 2):
			#ABP_NACK Results
			temp_result = []
			for j in BER:
				temp_result.append(ABP_NACK(timeoutNumberOne,j,H,L,C,tau[0]))

			for j in BER:
				temp_result.append(ABP_NACK(timeoutNumberTwo,j,H,L,C,tau[1]))

			ABP_NACK_Result.append(temp_result)



		if (mode == 3):
			#GBN Results
			temp_result = []
			for j in BER:
				temp_result.append(GBN(timeoutNumberOne,j,H,L,C,tau[0]))

			for j in BER:
				temp_result.append(GBN(timeoutNumberTwo,j,H,L,C,tau[1]))

			GBN_Result.append(temp_result)


	if (mode == 1):
		#Write results to ABP.csv
		with open("ABP.csv", "wb") as f:
			writer = csv.writer(f, delimiter = ",")
			for row in ABP_Result:
				writer.writerow(row)

	if (mode == 2):
		#Write results to ABPNACK.csv
		with open("ABP_NAK.csv", "wb") as f:
			writer = csv.writer(f, delimiter = ",")
			for row in ABP_NACK_Result:
				writer.writerow(row)

	if (mode == 3):
		#Write results to GBN.csv
		with open("GBN.csv", "wb") as f:
			writer = csv.writer(f, delimiter = ",")
			for row in GBN_Result:
				writer.writerow(row)




if __name__ == '__main__':
	main();

