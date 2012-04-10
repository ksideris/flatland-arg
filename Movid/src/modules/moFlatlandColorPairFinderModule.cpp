//guvcview

/***********************************************************************
 ** Copyright (C) 2010 Movid Authors.  All rights reserved.
 **
 ** This file is part of the Movid Software.
 **
 ** This file may be distributed under the terms of the Q Public License
 ** as defined by Trolltech AS of Norway and appearing in the file
 ** LICENSE included in the packaging of this file.
 **
 ** This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
 ** WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.
 **
 
 ** Contact info@movid.org if any conditions of this licensing are
 ** not clear to you.
 **
 **********************************************************************/

#include <stdio.h>
#include <assert.h>
#include <cstdlib>
#include "moFlatlandColorPairFinderModule.h"
#include "../moLog.h"
#include "cv.h"
#include <string>
#include <sstream>

#define WINDOW_SIZE 7

MODULE_DECLARE(FlatlandColorPairFinder, "native", "ColorPair Description");


#define RED 0
#define GREEN 1
#define BLUE 2
#define WHITE 3
#define MAX_N_LIGHTS 20
#define UNRECOGNIZED_PLAYER_COLOR_PAIR -1

moFlatlandColorPairFinderModule::moFlatlandColorPairFinderModule() : moImageFilterModule(){

	MODULE_INIT();

	this->storage = cvCreateMemStorage(0);

	this->output_data = new moDataStream("trackedblob");
	this->declareOutput(1, &this->output_data, new moDataStreamInfo("data", "trackedblob", "Data stream of type 'trackedblob'"));
	this->blobs = new moDataGenericList();
	this->players = new moDataGenericList();

	initialized=false;

	// since cvFindContour accept only one channel image, just change the input
	
	//TODO : demand colored input, possibly in HSV form
	//this->setInputType(0, "IplImage8");

	this->properties["min_size"] = new moProperty(2 * 2);
	this->properties["max_size"] = new moProperty(50 * 50);
	this->properties["num_players"] = new moProperty(0);
	this->properties["pair_distance"] = new moProperty(60);
	this->properties["color"] = new moProperty("RGB");
	this->properties["color"]->setChoices("RGB;HSV;YCBCR");
	this->frameCounter = 0;
}

moFlatlandColorPairFinderModule::~moFlatlandColorPairFinderModule() {
	cvReleaseMemStorage(&this->storage);
	delete this->blobs;
}

void moFlatlandColorPairFinderModule::clearBlobs() {
	moDataGenericList::iterator it;
	for ( it = this->blobs->begin(); it != this->blobs->end(); it++ )
		delete (*it);
	this->blobs->clear();
}
struct distance_node
{
	double distance;
	int count;
};
/***********************************************************
Name: 		getPlayerIndex
Author: 	Costas
Modified: 	2/8/2012
Parameters:
	ColoredPt color1 - first blob to match
	ColoredPt color2 - second blob to match
	double avX	 - the x coordinate of the pair location
	double avY	 - the y coordinate of the pair location
	bool init	 - flag for initialization of the process
return:
	id of the matched player	
************************************************************/
int moFlatlandColorPairFinderModule::getPlayerIndex(ColoredPt color1, ColoredPt color2 ,double avX,double avY,bool init)
{	

	int id=-1;
		
	if(init) // If we are just initializing , we need to create a list with all the players. The indices are assigned serially upon discovery of player
	{	
		struct Player* pl = new Player();
		pl->point1 =color1;
		pl->point2 =color2;
		pl->x=avX;
		pl->y=avY;		
		if(Players.empty()) 
			pl->id=0;
		else 
		{
		
			pl->id=Players.back().id+1;
		
		}
	
		id=pl->id;
		//std::cout << "ID OF USER "<<id<<std::endl;		
		this->Players.push_back(*pl);
	}
	else // if exists a list of players, try to match the color pair tbased on the norm2 of RGB color code //TODO - could HSV or YCbCr work better?
	{	
		int index=-1;
		double mindistance=1000000;
		
		for(int k=0;k<Players.size();k++)
		{
			
		if(!Players[k].updated)
		{
			double dist1 = pow(Players[k].point1.red-color1.red,2)+pow(Players[k].point1.green-color1.green,2)+pow(Players[k].point1.blue-color1.blue,2)+pow(Players[k].point2.red-color2.red,2)+pow(Players[k].point2.green-color2.green,2)+pow(Players[k].point2.blue-color2.blue,2);
			double dist2 = pow(Players[k].point2.red-color1.red,2)+pow(Players[k].point2.green-color1.green,2)+pow(Players[k].point2.blue-color1.blue,2)+pow(Players[k].point1.red-color2.red,2)+pow(Players[k].point1.green-color2.green,2)+pow(Players[k].point1.blue-color2.blue,2);
			dist1=sqrt(dist1);
			dist2=sqrt(dist2);
			
			//printf("Pl%d   Point1   :   %6.3f %6.3f %6.3f\n",k,Players[k].point1.red,Players[k].point1.green,Players[k].point1.blue);
			//printf("Pl%d   Point2   :   %6.3f %6.3f %6.3f\n",k,Players[k].point2.red,Players[k].point2.green,Players[k].point2.blue);
			//printf("Curr.  Point1   :   %6.3f %6.3f %6.3f\n",color1.red,color1.green,color1.blue);
			//printf("Curr.  Point2   :   %6.3f %6.3f %6.3f\n",color2.red,color2.green,color2.blue);
			
			if(dist1>=dist2 && dist2<mindistance)
			{
				mindistance=dist2;
				index=k;
			}
			else if(dist2>=dist1 && dist1<mindistance)
			{
				mindistance=dist1;
				index=k;
			}
		}
		}
		if(index>-1) // when the min distance is found , update the 
		{
		
		
		
		Players[index].updated=true;
		Players[index].x=avX;
		Players[index].y=avY;
		
		int x=0;
			
		}
		
	}		
	
	return id;

}

/***********************************************************
Name: 		MatchPlayers
Author: 	Costas
Modified: 	2/8/2012
Parameters:
	std::vector<ColoredPt> cPts - the discovered blobs
	int *pairs	 - the discovered pairs
	
return:
	void	
************************************************************/
void moFlatlandColorPairFinderModule::MatchPlayers(int *pairs,std::vector<ColoredPt> cPts,bool init)
{

	// look at pair colors and determine player number
	for (int i = 0; i < MAX_N_LIGHTS; i++)
	{
		if (pairs[i] >= 0)
		{
			
			int color1 = cPts[i].color;
			int color2 = cPts[pairs[i]].color;

			
			double avX = (cPts[i].x + cPts[pairs[i]].x)/2;
			double avY = (cPts[i].y + cPts[pairs[i]].y)/2;	
			
			getPlayerIndex(cPts[i], cPts[pairs[i]],avX,avY,init);
			
			
		}
	}

}
/***********************************************************
Name: 		FindPairs
Author: 	Costas (Partial Code by Alex)
Modified: 	2/19/2012
Parameters:
	std::vector<ColoredPt> cPts - the discovered blobs
	bool init	 - the initialization flag
	
return:
	int nPlayersFound - number of player found	
************************************************************/
int moFlatlandColorPairFinderModule::FindPairs(std::vector<ColoredPt> cPts,bool init)
{
	int nPlayersFound=0;
	int pairs[MAX_N_LIGHTS];
	
	int max_distance = this->property("pair_distance").asInteger();	
	for ( int i = 0; i < MAX_N_LIGHTS; i++ )
	{
		pairs[i] = -1;
	}
	
	//!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
	// In more realistic scenarios, an arbitrary number of lights is likely to appear!
	// Need to account for this!
	
	for ( int i = 0; i < cPts.size() && i < MAX_N_LIGHTS; i++ ) // dynamically allocate pairs based on number of lights?
	{

		if(pairs[i] == -1)
		{
			double minDist = 1000000;//distances are < 1, so should be OK.
			int closestIdx = -1;
			for ( int j = i; j < cPts.size() && j < MAX_N_LIGHTS; j++ )
			{
				if (j != i)
				{
				double x1 = cPts[i].x;
				double y1 = cPts[i].y;

				double x2 = cPts[j].x;
				double y2 = cPts[j].y;
				
				double distance = sqrt((x2 - x1)*(x2 - x1) + (y2 - y1)*(y2 - y1));
				if (distance < minDist && distance < max_distance) //TODO make 
				{
					minDist = distance;
					closestIdx = j;
				}
				}
			}
			if (closestIdx >= 0)
			{
				pairs[i] = closestIdx;
				pairs[closestIdx] = -9999; //designate as 'slave' point.
				nPlayersFound ++;
				

			}
		}
		
	}
	
	MatchPlayers(pairs,cPts,init);
	
	return nPlayersFound;
}
/***********************************************************
Name: 		applyFilter
Authors: 	Alex , Costas
Modified: 	2/19/2012
Parameters:
	IplImage *src -  the input frame
	
return:
	void	
************************************************************/
void moFlatlandColorPairFinderModule::applyFilter(IplImage *src) {

/////////////////////////////////////////////////////////////////////////////////////
	//Step 1 get gray version of input, retain colored version

/////////////////////////////////////////////////////////////////////////////////////
	//Step 2 pass gray along normally to contour finder.

	this->clearBlobs();
	
	imagePreprocess(src);
	
	cvCvtColor(src, this->output_buffer, CV_RGB2GRAY);
	
	CvSeq *contours = 0;
	cvFindContours(this->output_buffer, this->storage, &contours, sizeof(CvContour), CV_RETR_CCOMP);

    	cvDrawContours(this->output_buffer, contours, cvScalarAll(255), cvScalarAll(255), 100);

    	// Consider each contour a blob and extract the blob infos from it.
	int size;
	int min_size = this->property("min_size").asInteger();
	int max_size = this->property("max_size").asInteger();
	CvSeq *cur_cont = contours;

	IplImage *tmp = cvCreateImage(cvGetSize(src),src->depth,src->nChannels);
	
	 std::string ColorMode = this->property("color").asString();
	if(ColorMode == "HSV")
		cvCvtColor(src, tmp, CV_RGB2HSV);
	else if(ColorMode == "YCBCR")
		cvCvtColor(src, tmp, CV_RGB2YCrCb);

	cvCopy(src,tmp);
	
	//convert Color for image
		
/////////////////////////////////////////////////////////////////////////////////////
	//Step 3 check window around contour centers and find color

	
	std::vector<ColoredPt> cPts;	

	//printf("==================================\n");
	int blobi = 0;
	while (cur_cont != 0) 
	{
		CvRect rect	= cvBoundingRect(cur_cont, 0);
		size = rect.width * rect.height;
		//printf(":: %d\n", size);
		if ((size >= min_size) && (size <= max_size)) {

			//TODO use a Vector
			double red = 0;
			double green = 0;
			double blue = 0;
			int blobColor = 0;
			//in reality, probably could filter heavily and just look at 1 pixel, or at least a very small window
			
			// [!!!] 
			int pixelcount=0;			
			for (int x = rect.x; x < rect.x + rect.width; x++)
			{
				for (int y = rect.y; y < rect.y + rect.height; y++)
				{
					int blueVal  = ( ((uchar*)(src->imageData + src->widthStep*y))[x*3+0] );
					int greenVal = ( ((uchar*)(src->imageData + src->widthStep*y))[x*3+1] );
					int redVal   = ( ((uchar*)(src->imageData + src->widthStep*y))[x*3+2] );
					
					double colorNorm = (blueVal) + (greenVal) + ( redVal);

					//weight dark pixels less					
					double weight = 1.0;//(1.0*blueVal + greenVal + redVal) / (1.5 * 255.0);
					if (weight > 1) 
					{
						weight = 1;
					}
					
					if (colorNorm > 30)
					{
						red += weight*redVal/colorNorm;
						green += weight*greenVal/colorNorm;
						blue += weight*blueVal/colorNorm;

						pixelcount++;
					}
				}
			}
			red = red/pixelcount;
			green = green/pixelcount;
			blue = blue/pixelcount;
			
		
			if(red > green && red>blue)
				blobColor=RED;
			else if(green > red && green>blue)
				blobColor=GREEN;
			else if(blue > red && blue>green)
				blobColor=BLUE;
			else
				blobColor=WHITE;

				
		
			blobi++;

			struct ColoredPt thisPt;

			thisPt.red =red;
			thisPt.green =green;
			thisPt.blue =green;
			thisPt.x = (rect.x + rect.width / 2);// / (double) src->width;
			thisPt.y = (rect.y + rect.height / 2);// / (double) src->height;
			thisPt.color = blobColor;	

			cPts.push_back(thisPt);
			

		// Draw a letter corresponding to the LED color
		CvFont font;
		cvInitFont(&font, CV_FONT_HERSHEY_PLAIN, .7f, .7f, 0, 1, CV_AA);
	
		if (blobColor == RED)
		{
    			cvPutText(this->output_buffer, "R", cvPoint(rect.x + rect.width / 2.0, rect.y + rect.height / 2.0),  &font, cvScalar(255, 255, 255, 0));
		} 
		else 	if (blobColor == GREEN)
		{
    			cvPutText(this->output_buffer, "G", cvPoint(rect.x + rect.width / 2.0, rect.y + rect.height / 2.0),  &font, cvScalar(255, 255, 255, 0));
		} 
			else if (blobColor == BLUE)
		{
    			cvPutText(this->output_buffer, "B", cvPoint(rect.x + rect.width / 2.0, rect.y + rect.height / 2.0),  &font, cvScalar(255, 255, 255, 0));
		} 
		else if (blobColor == WHITE)
		{
    			cvPutText(this->output_buffer, "Y", cvPoint(rect.x + rect.width / 2.0, rect.y + rect.height / 2.0),  &font, cvScalar(255, 255, 255, 0));
		}

		}
		cur_cont = cur_cont->h_next;
	}


	int nPlayersFound = 0;
	//Init the adjacency list	
	int num_players = this->property("num_players").asInteger();		
	
	if(!initialized)
	{	
			int players_found = FindPairs(cPts,true);
			printf("No Players:%d\n",players_found);
			if(players_found != num_players) // KEEP initializing as long as  we haven't reached the desired players
			{
				printf("No Players doesn't match input value : %d <> %d\n",players_found,num_players);
				Players.clear();
			}
			else
			{
				printf("Initialization Complete: \n");
				initialized=true;
			}
				
	
	}
	else
	{
		FindPairs(cPts,false);
	}
	
	moDataGenericList::iterator pit;
	for ( pit = this->players->begin(); pit != this->players->end(); pit++ )
	{
		delete (*pit);
	}	
	this->players->clear();
	
	for(int i=0;i<Players.size();i++)
	{
		// Debugging info: Output Player ID on filtered image
		Players[i].updated =false;
		CvFont font;
		cvInitFont(&font, CV_FONT_HERSHEY_PLAIN, 1.7f, 1.7f, 0, 1, CV_AA);			
		std::ostringstream labelStream;
		labelStream << Players[i].id;

		cvPutText(this->output_buffer, labelStream.str().c_str(), cvPoint(Players[i].x, Players[i].y),  &font, cvScalar(255, 255, 255, 0));
		
		// Convert Internal Player List to Output LIST (taken from Alex's code
		moDataGenericContainer *player = new moDataGenericContainer();
		player->properties["implements"] = new moProperty("pos");
		player->properties["x"] = new moProperty(Players[i].x / (double) src->width );/// src->width);
		player->properties["y"] = new moProperty(Players[i].y / (double) src->height);/// src->height);
		player->properties["blob_id"] = new moProperty(Players[i].id);

		std::string implements = player->properties["implements"]->asString();
		//// Indicate that the blob has been tracked, i.e. blob_id exists.
		implements += ",tracked";
		player->properties["implements"]->set(implements);
		
		/*
		moDataGenericContainer *blob = new moDataGenericContainer();
			blob->properties["implements"] = new moProperty("pos,size");
			blob->properties["x"] = new moProperty((rect.x + rect.width / 2) / (double) src->width);
			blob->properties["y"] = new moProperty((rect.y + rect.height / 2) / (double) src->height);
			blob->properties["width"] = new moProperty(rect.width);
			blob->properties["height"] = new moProperty(rect.height);
			this->blobs->push_back(blob);
		*/
		printf("%f,%f,%d\n",Players[i].x /(double) src->width ,Players[i].y/(double)src->height,Players[i].id  );
		this->players->push_back(player);
		
	}
	
			
		
	//frameCounter++;
	
	
	//commented code 3
	
	//FLUSH DATA
    	this->output_data->push(this->players);
}

void moFlatlandColorPairFinderModule::allocateBuffers() {
	
	IplImage* src = static_cast<IplImage*>(this->input->getData());
	if ( src == NULL )
		return;
	this->output_buffer = cvCreateImage(cvGetSize(src),src->depth, 1);	//only one channel
	LOG(MO_DEBUG, "allocated output buffer for GrayScale module.");
}

bool moFlatlandColorPairFinderModule::compareColorPair(int colorA1, int colorA2, int colorB1, int colorB2)
{
	return (colorA1 == colorB1 && colorA2 == colorB2) || (colorA1 == colorB2 && colorA2 == colorB1);
}


void moFlatlandColorPairFinderModule::imagePreprocess(IplImage *src){

//TODO : make the parameters accessible from the preset files

	IplConvKernel *element = 0;//the pointer for morphological strucutre
	
	//Then erode and dilate the image
	IplImage *tmp = cvCreateImage(cvGetSize(src),src->depth,src->nChannels);
	element = cvCreateStructuringElementEx(3,3,1,1,CV_SHAPE_ELLIPSE,0);//erode and dilate element

	//cvErode(src, tmp, element,1);//erode the image
	cvCopy(src,tmp);	
	cvSmooth(src,src,CV_GAUSSIAN,9,0,0,0);//median filter, elliminate small noise

	cvDilate(tmp, src, element,5);//dilate the image
	cvReleaseImage(&tmp);

}

// OLD CODE, USED TO MATCH PLAYERS BASED ON COLOR
int moFlatlandColorPairFinderModule::matchColor(int r, int g, int b) {

	//TODO : move this constant array to top of file
	int colors [][3] =
	{
	{1,0,0},// RED
	{0,1,0},// GREEN
	{0,0,1},// BLUE
	
	//WHITE MUST BE THE LAST COLOR IN THIS ARRAY!
	{1,1,1}// WHITE
	};
	int NColor = 4;
	
	int ID = -1;//no match

	
	int a1[3];
	int a2[3];
	double l1,l2;
	double sim;
	double threshold = 0.5;
	double whiteThreshold = .95;
	
		a2[0] = r;
		a2[1] = g;
		a2[2] = b;

	int bestMatch = -1;
	int bestSim = -10000;
	double bestDist = 100000;

	for(int i = 0; i< NColor; i++)
	{
		a1[0] = colors[i][0];
		a1[1] = colors[i][1];
		a1[2] = colors[i][2];

		l1 = a1[0]*a1[0]+a1[1]*a1[1]+a1[2]*a1[2];
		l2 = a2[0]*a2[0]+a2[1]*a2[1]+a2[2]*a2[2];
		sim = (a1[0]*a2[0]+a1[1]*a2[1]+a1[2]*a2[2])/sqrt(l1*l2);

		//Decide based on dot product:
				
		if(sim > threshold && sim > bestSim)
		{
			// NOTE:
			// White is virtually always the most similar color to an LED, when looking at the dot product.
			// Thus, it is necessary to have a more stringent threshold for matching to white.
			
			if (i != WHITE || sim > whiteThreshold)
			{			
				bestMatch = i;	
				bestSim = sim;
			}
			//return (i);
		}
		
		//Decide based on euclidean distance
		/*double dr = a1[0] - a2[0];
		double dg = a1[1] - a2[1];
		double db = a1[2] - a2[2];
		double distance = sqrt(dr*dr + dg*dg + db*db);
		if (distance < bestDist)
		{
			bestMatch = i;	
			bestDist = distance;
		}*/
		
	}
	return bestMatch;//-1;
}
