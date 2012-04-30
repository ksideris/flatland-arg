
import cv , liblo, sys ,random,math,time

ESC_KEY = 27
USE_CAM =False
RECORDINGS_FOLDER = '/home/costas/flatland-arg/trackingTest/'
VIDEO_FILE = RECORDINGS_FOLDER+'edaTest.avi'
THRESHOLD_VALUE = 30
COLOR_THRESHOLD_VALUE = 60
EROSION_ROUNDS = 1
DILATION_ROUNDS = 1
GAUSSIAN_SIZE =3
PAIR_RANGE =60
MATCHING_THRESHOLD = 60
HISTORY_FRAMES=3
SMOOTHING_WEIGHT = 0.1 # between 0 and 1
DEBUG = False
RECORD = False
RECORDING = RECORDINGS_FOLDER +'recording'+ str(int(time.time()))+'.avi'

print RECORDING
def LowPassFilter(signal):
	
	value=signal[0]
	for i in range(1,len(signal)):
		value = SMOOTHING_WEIGHT*signal[i]+(1.0-SMOOTHING_WEIGHT)*value;
	return value
	
class ColorBlob:

	x	=0
	y	=0
	color	= (0,0,0)
	size	=0
	blobid	=0
	histogram =[]
	matched= False
	
		
class Player:

	signature = (0,0,0,0,0,0)
	xhist	= []
	yhist	= []
	_id	=0
	updated= False
	def __init__(self):
    		self.xhist = []
    		self.yhist = []
	def PushX(self,_x):
		self.xhist.append(_x)
		if(len(self.xhist) >HISTORY_FRAMES):
			self.xhist.remove(self.xhist[0])
		
		self.x = LowPassFilter(self.xhist) 
	def PushY(self,_y):
		self.yhist.append(_y)
		
		if(len(self.yhist) >HISTORY_FRAMES):
			self.yhist.remove(self.yhist[0])	
		self.y = LowPassFilter(self.yhist) 



def Preprocess(frame):

	output=cv.CreateImage(cv.GetSize(frame), cv.IPL_DEPTH_8U, 1)
		
	cv.CvtColor(frame,output,cv.CV_BGR2GRAY);
	    	
	cv.Threshold(output,output, THRESHOLD_VALUE,255,cv.CV_THRESH_BINARY) 
	
	pos=1
	element = cv.CreateStructuringElementEx(pos*2+1, pos*2+1, pos, pos, cv.CV_SHAPE_ELLIPSE)
	 
	cv.Erode(output,output,element,EROSION_ROUNDS)
	
	cv.Smooth(output,output,cv.CV_GAUSSIAN,GAUSSIAN_SIZE,0,0,0);
	cv.Dilate(output,output,element,DILATION_ROUNDS)
	
	return output
def ResetBlobs(Blobs):
	for blob in Blobs:
		blob.matched=False
		
def MatchDescriptorBlob(newBlob):
	minBlobidx=-1
	minDist =100000
	for idx,blob in enumerate(Blobs):
		if(not blob.updated):
			dist = math.sqrt( 100*pow(newBlob.color[0]-blob.color[0],2)+pow(newBlob.color[1]-blob.color[1],2))
			if(minDist > dist):
				minDist=dist
				minBlobidx = idx
			
	
	if(minBlobidx==-1):
		newBlob.blobid = len(Blobs)
		Blobs.append(newBlob)
	else:
		newBlob.blobid = Blobs[minBlobidx].blobid
		Blobs[minBlobidx].updated =True
	
	return newBlob		
		
def ResetPlayers(Players):
	for player in Players:
		player.updated=False
	return Players	

def WeightedVectorEucl(v1,v2,weight):
	return math.sqrt(\
			weight/2.0* pow(v1[0]-v2[0],2) + weight/2.0* pow(v1[2]-v2[2],2)+\
			1/2.0* pow(v1[1]-v2[1],2) +1/2.0* pow(v1[3]-v2[3],2) 	)	

def InitializeClusters(Clusters):
	print Clusters
	for cluster in (Clusters):
		if(len(cluster[1])>1) :
			print cluster
			print 'Cannot initialize, players are too close to each other'
			return -1
		else:
			for othercluster in (Clusters):
				if(othercluster[1][0]==cluster[0]):
					Clusters.remove(othercluster)
					break

	return Clusters

def InitializePlayers(Players,players,Blobs):
	
	
	Players = []
	for player in players:
		p = Player()
		p.signature = Blobs[player[1][0]].color+Blobs[player[1][1][0]].color;
		p.PushX( player[1][2][0] )
		p.PushY( player[1][2][1] )
		p._id = player[0]
		Players.append(p)
		
	return Players
		
def ResolveClusters(Players,Blobs,Clusters):
	
	
	Signatures = [] 
	for cluster in (Clusters):
		for neighbor in cluster[1]:
			Signatures.append(((cluster[0],neighbor),Blobs[cluster[0]].color+Blobs[neighbor].color))
			
	
	for player in Players:	
		if(not player.updated):
			minIdx=-1
			minDist =100000
			for idx,signature in enumerate(Signatures):
				color_delta= WeightedVectorEucl(player.signature,signature[1],1) 
				x = (Blobs[signature[0][0]].x + Blobs[signature[0][1]].x)/2.0
				y = (Blobs[signature[0][0]].y + Blobs[signature[0][1]].y)/2.0
				pos_dist = math.sqrt(pow(player.x-x,2.0)+pow(player.y-y,2.0))
				dist = color_delta  + 0.1*pos_dist 
				if( pos_dist< MATCHING_THRESHOLD and dist < minDist ):
					minDist = dist
					minIdx = idx
			if(minIdx>-1):
				player.updated=True
				player.PushX( (Blobs[Signatures[minIdx][0][0]].x + Blobs[Signatures[minIdx][0][1]].x)/2.0 )
				player.PushY( (Blobs[Signatures[minIdx][0][0]].y + Blobs[Signatures[minIdx][0][1]].y)/2.0 )
	
	return Players
	
def FindClusters(Blobs,Range):
	Clusters = [] 
	
	for idx,blob in enumerate(Blobs):
		
		Neighbors =[]
		for cand_idx,candidate in enumerate(Blobs):
			if(idx <> cand_idx):
				dist = math.sqrt( pow(candidate.x-blob.x,2)+pow(candidate.y-blob.y,2))
				if(dist < Range ):
					Neighbors.append( cand_idx )
		if(len(Neighbors)>0):
			Clusters.append( (idx,Neighbors, (blob.x,blob.y) ) )
						
	return Clusters				
	
def GetContourDescriptor(contour,src):
	rect = cv.BoundingRect(contour)	
	h=0
	s=0
	v=0
	for i in range(rect[1],rect[1]+ rect[3]-1): 
    		for j in range(rect[0],rect[0]+ rect[2]-1): 
		    	pixel_value = cv.Get2D(src, i, j) 
				# Since OpenCV loads color images in BGR, not RGB 
			cv.Set2D(src, i, j, (0,0,0) )
			if(pixel_value[2]>COLOR_THRESHOLD_VALUE):
				h += pixel_value[0]
				s += pixel_value[1]*2
				v += pixel_value[2]
				cv.Set2D(src, i, j, (pixel_value[0],pixel_value[1]*2 ,pixel_value[2],pixel_value[3])) 
	
	h /= rect[2]*rect[3]
	s /= rect[2]*rect[3]
	v /= rect[2]*rect[3]
	
	
	return (h,s,v) 
		
def main():

	#Set Up Server Connection
	try:
    		target = liblo.Address(1234)
	except liblo.AddressError, err:
    		print str(err)
    		sys.exit()
	#end of network con
	
	if(USE_CAM):
		capture =cv.CaptureFromCAM(0)		
		fps =  int (cv.GetCaptureProperty( capture, cv.CV_CAP_PROP_FPS ));
	else:
		capture = cv.CaptureFromFile(VIDEO_FILE)
		fps =  30

	frameCount = 0
	key=0    
	width,height = cv.GetSize(cv.QueryFrame( capture ) )
	
	if(RECORD):
		
		writer = cv.CreateVideoWriter(RECORDING,cv.CV_FOURCC('D', 'I', 'V', 'X'),fps,(width,height))
	
	Players = []
	
	while( key != ESC_KEY ) : 
	  		 
		frame = cv.QueryFrame( capture ) 
		if(RECORD):
			cv.WriteFrame(writer, frame)
		if frame == None:
			print "END OF VIDEO"
			cv.WaitKey()
			break         
	
		output = Preprocess(frame)
	 	
		contours = cv.FindContours (output, cv.CreateMemStorage(0) , cv.CV_RETR_CCOMP)
		
		cv.DrawContours(frame, contours, cv.ScalarAll(125), cv.ScalarAll(125), 100);
		contour=contours
		_id=0
		
		bundle = liblo.Bundle(liblo.time(), liblo.Message('/Start'))
		Blobs = []
				
		cv.CvtColor(frame,frame,cv.CV_BGR2HSV);
		
		while contour is not None:
   			
   			rect = cv.BoundingRect(contour)
			
   			c = ColorBlob()
   			
   			color = GetContourDescriptor(contour,frame)
   			c.color = (color[0],color[1])
   			c.x = rect[0] + rect[2] / 2-1
   			c.y = rect[1] + rect[3] / 2-1 
   			Blobs.append(c)
   			if(DEBUG):
	   			font = cv.InitFont(cv.CV_FONT_HERSHEY_SIMPLEX, .7, .7, 0, 1, 8) 
				cv.PutText(frame,'HSV: '+str(int(color[0]))+','+ str(int(color[1]))+','+ str(int(color[2])), (rect[0] + rect[2] / 2-1, rect[1] + rect[3] / 2-1),font, cv.ScalarAll(125)) 
			
			
			_id+=1
			contour = contour.h_next()
			
			
		Clusters = FindClusters(Blobs,PAIR_RANGE)
		Players = ResetPlayers(Players)
		Players  = ResolveClusters(Players,Blobs,  Clusters)
		
		
		
		for idx,player in enumerate(Players):
			font = cv.InitFont(cv.CV_FONT_HERSHEY_SIMPLEX, .7, .7, 0, 1, 8) 
			cv.PutText(frame,str(player._id), (int(player.x),int(player.y)),font, (100,100,100)) 
			bundle.add(liblo.Message("/trackingPoints", player._id,player.x/height, player.y/width))
			
			
		cv.CvtColor(frame,frame,cv.CV_HSV2BGR);
				
		key = cv.WaitKey( 1000 / fps ) & 0xFF;  
		
		if( key  == 105 ):
			font = cv.InitFont(cv.CV_FONT_HERSHEY_SIMPLEX, .7, .7, 0, 1, 8) 
			cv.PutText(frame,'To initialize, insert numbers for the Highlighted Player', (0,height-20),font,  cv.ScalarAll(125))
			playerids = []
			ReducedClusters = InitializeClusters(Clusters)
			print ReducedClusters
			
			for idx,cluster in enumerate(ReducedClusters):
				copy =cv.CreateImage(cv.GetSize(frame),frame.depth, frame.channels)
				cv.Copy(frame,copy)
				cv.Circle(copy,(int(cluster[2][0]),int(cluster[2][1])),PAIR_RANGE,(255,0,0),10)
				
				cv.ShowImage("Initialization Screen", copy)
				key=-1
				while(key < 48 or key > 57):
					key = cv.WaitKey()& 0xFF
					
				playerids.append((key-48,cluster))					
					
				
			print playerids
			key = cv.WaitKey() & 0xFF
			cv.DestroyWindow("Initialization Screen")
			Players=InitializePlayers(Players,playerids,Blobs)
			print Players
			
		else:
			cv.ShowImage( "video", frame );  
			 		
		
		bundle.add(liblo.Message("/End"))
		liblo.send(target, bundle)
	       
		
 		
if __name__ == '__main__':
 	main()

