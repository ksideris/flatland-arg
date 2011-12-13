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

struct ColoredPt
{
	double x;
	double y;
	int color;
};

#define RED 0
#define GREEN 1
#define BLUE 2
#define WHITE 3

#define UNRECOGNIZED_PLAYER_COLOR_PAIR -1

moFlatlandColorPairFinderModule::moFlatlandColorPairFinderModule() : moImageFilterModule(){

	MODULE_INIT();

	this->storage = cvCreateMemStorage(0);

	this->output_data = new moDataStream("trackedblob");
	this->declareOutput(1, &this->output_data, new moDataStreamInfo("data", "trackedblob", "Data stream of type 'trackedblob'"));
	this->blobs = new moDataGenericList();
	this->players = new moDataGenericList();

	// since cvFindContour accept only one channel image, just change the input
	
	//TODO : demand colored input, possibly in HSV form
	//this->setInputType(0, "IplImage8");

	this->properties["min_size"] = new moProperty(2 * 2);
	this->properties["max_size"] = new moProperty(50 * 50);
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

void moFlatlandColorPairFinderModule::applyFilter(IplImage *src) {

/////////////////////////////////////////////////////////////////////////////////////
	//Step 1 get gray version of input, retain colored version

/////////////////////////////////////////////////////////////////////////////////////
	//Step 2 pass gray along normally to contour finder.

	this->clearBlobs();
	
	//imagePreprocess(src);
	//cvCopy(src, this->output_buffer);
	cvCvtColor(src, this->output_buffer, CV_RGB2GRAY);
	
	    CvSeq *contours = 0;
	cvFindContours(this->output_buffer, this->storage, &contours, sizeof(CvContour), CV_RETR_CCOMP);

    cvDrawContours(this->output_buffer, contours, cvScalarAll(255), cvScalarAll(255), 100);

    //cvCircle(this->output_buffer,                       /* the dest image */
    //         cvPoint(110, 60), 35,      /* center point and radius */
    //         cvScalarAll(255),    /* the color; red */
      //       1, 8, 0); 


	// Consider each contour a blob and extract the blob infos from it.
	int size;
	int min_size = this->property("min_size").asInteger();
	int max_size = this->property("max_size").asInteger();
	CvSeq *cur_cont = contours;

	
		
/////////////////////////////////////////////////////////////////////////////////////
	//Step 3 check window around contour centers and find color

	//clear the console?
	//system("cls");
	//system("clear");
	//clrscr();
	//printf("\033[2J");
	//std::cout << std::string( 100, '\n' );	

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
			for (int x = rect.x; x < rect.x + rect.width; x++)
			{
				for (int y = rect.y; y < rect.y + rect.height; y++)
				{
					int blueVal = ( ((uchar*)(src->imageData + src->widthStep*y))[x*3+0] );
					int greenVal = ( ((uchar*)(src->imageData + src->widthStep*y))[x*3+1] );
					int redVal = ( ((uchar*)(src->imageData + src->widthStep*y))[x*3+2] );
					
					double colorNorm = 1.0;//sqrt((blueVal*blueVal) + (greenVal*greenVal) + (redVal * redVal));

					//weight dark pixels less					
					double weight = 1.0;//(1.0*blueVal + greenVal + redVal) / (1.5 * 255.0);
					if (weight > 1) 
					{
						weight = 1;
					}
					
					if (colorNorm > 0)
					{
						red += weight*redVal/colorNorm;
						green += weight*greenVal/colorNorm;
						blue += weight*blueVal/colorNorm;
					}
				}
			}

			//the channel totals
			//printf("%d : %f\n%f\n%f\n\n",blobi , red, green, blue);
			blobi++;

			if (red > green && red > blue)
			{
				blobColor = RED;
			}

			if (blue > green && blue > red)
			{
				blobColor = BLUE;
			}

			if (green > red && green > blue)
			{
				blobColor = GREEN;
			}
			

			blobColor = matchColor(red, green, blue);			

			

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


		/*moDataGenericContainer *blob = new moDataGenericContainer();
		blob->properties["implements"] = new moProperty("pos,size");
			blob->properties["x"] = new moProperty((rect.x + rect.width / 2) / (double) src->width
			);
			blob->properties["y"] = new moProperty((rect.y + rect.height / 2) / (double) src->height
			);
			blob->properties["width"] = new moProperty(rect.width);
			blob->properties["height"] = new moProperty(rect.height);
			blob->properties["color"] = new moProperty(blobColor);


			this->blobs->push_back(blob);*/

			struct ColoredPt thisPt;
			thisPt.x = (rect.x + rect.width / 2);// / (double) src->width;
			thisPt.y = (rect.y + rect.height / 2);// / (double) src->height;
			thisPt.color = blobColor;	

			cPts.push_back(thisPt);

		}
		cur_cont = cur_cont->h_next;
	}

/////////////////////////////////////////////////////////////////////////////////////
	//Step 4 iterate over blobs again, to find close pairs

//TODO Currently, this algorithm assumes the best, and does nothing to ensure robustness/smoothness
//e.g. add a distance threshold (would need to be "settable" in a Gui)

	int nPlayersFound = 0;
	//Init the adjacency list	

	int MAX_N_LIGHTS = 20; // TODO! more lights may need to be identified for field markers!
		
	int pairs[MAX_N_LIGHTS];
	for ( int i = 0; i < MAX_N_LIGHTS; i++ )
	{
		pairs[i] = -1;
	}
	
	//printf("+++++++++++++++++++++++++++++++++++++++++\n");
	// map out closest pairs of lights.

	//TODO need to iterate through blobs and throw out obviously non-player-light blobs. (big blobs)

	//TODO
	//TODO
	//TODO
	//!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
	// In more realistic scenarios, an arbitrary number of lights is likely to appear!
	// Need to account for this!
	//! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! 
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
				if (distance < minDist)
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
				//printf("%d ___ %d\n",i, pairs[i]);
				}
		}
		else
		{
		
		}
	}

	//printf("==================================\n");
	//for ( int i = 0; i < cPts.size(); i++ )
	//{
	//	printf("%d ___ %d\n", i, pairs[i]);
	//}

	///////////////////////////////////////
	// Clear the player list //////////////
	
	moDataGenericList::iterator pit;
	for ( pit = this->players->begin(); pit != this->players->end(); pit++ )
	{
		delete (*pit);
	}	
	this->players->clear();
	

	// look at pair colors and determine player number
	for (int i = 0; i < MAX_N_LIGHTS; i++)
	{
		if (pairs[i] >= 0)
		{
			//printf("%d ___ %d\n",pairs[i], pairs[i]);
			int color1 = cPts[i].color;
			int color2 = cPts[pairs[i]].color;

			//write a function to choose the player

			int playerIdx = getPlayerIndex(color1, color2);
			std::ostringstream labelStream;
			labelStream << playerIdx;

			/*if ((color1 == 0 && color2 == 2) || (color2 == 0 && color1 == 2)) //red and blue
			{
				label = "1";
			}
			else if ((color1 == 0 && color2 == 1) || (color2 == 0 && color1 == 1)) //red and green
			{
				label = "2";
			}*/
			
			double avX = (cPts[i].x + cPts[pairs[i]].x)/2;
			double avY = (cPts[i].y + cPts[pairs[i]].y)/2;	
			
			CvFont font;
			cvInitFont(&font, CV_FONT_HERSHEY_PLAIN, 1.7f, 1.7f, 0, 1, CV_AA);			

			cvPutText(this->output_buffer, labelStream.str().c_str(), cvPoint(avX, avY),  &font, cvScalar(255, 255, 255, 0));
			

			/*moDataGenericContainer *player = new moDataGenericContainer();
			player->properties["implements"] = new moProperty("pos");
			player->properties["x"] = new moProperty(avX / src->width);
			player->properties["y"] = new moProperty(avY / src->height);
			player->properties["blob_id"] = new moProperty(playerIdx);

			std::string implements = player->properties["implements"]->asString();
			// Indicate that the blob has been tracked, i.e. blob_id exists.
			implements += ",tracked";
			player->properties["implements"]->set(implements);

			this->players->push_back(player);*/

			//->properties["blob_id"]->set(old_id);
		}
	}
	
	//Add in some fake players, so I don't have to have the lights out to test the connection.
			double debugX = .5 + .25 * sin(2*3.14 * frameCounter / 200);			
			
			if (frameCounter % 2 == 0)
			{
			moDataGenericContainer *player = new moDataGenericContainer();
			player->properties["implements"] = new moProperty("pos");
			player->properties["x"] = new moProperty(debugX);
			player->properties["y"] = new moProperty(.75);
			player->properties["blob_id"] = new moProperty(0);

			std::string implements = player->properties["implements"]->asString();
			// Indicate that the blob has been tracked, i.e. blob_id exists.
			implements += ",tracked";
			player->properties["implements"]->set(implements);


			moDataGenericContainer *player2 = new moDataGenericContainer();
			player2->properties["implements"] = new moProperty("pos");
			player2->properties["x"] = new moProperty(1 - debugX);
			player2->properties["y"] = new moProperty(.75);
			player2->properties["blob_id"] = new moProperty(1);


			player2->properties["implements"]->set(implements);

				this->players->push_back(player);
				this->players->push_back(player2);
			}
			frameCounter = (frameCounter + 1) % 200;
			
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

int moFlatlandColorPairFinderModule::getPlayerIndex(int color1, int color2)
{	
	//printf("colors: %d, %d\n", color1, color2);
	int playerNumber = UNRECOGNIZED_PLAYER_COLOR_PAIR;
	int nPlayers = 10;
	int colorPairs [] [2] = 
	{
	{RED, BLUE}, //0
	{RED, GREEN},//1
	{RED, RED},//2
	{GREEN, BLUE},//3
	{GREEN, GREEN},//4
	{BLUE, BLUE} //5
	,{WHITE, WHITE} //6
	,{WHITE, RED} //7
	,{WHITE, BLUE} //8
	,{WHITE, GREEN} //9 
	//10 players total
	};

	int nMatches = 0;
	for (int i = 0; i < nPlayers; i++)
	{
	//printf("        %d, %d\n",  colorPairs[i][0], colorPairs[i][1]);
		if ( compareColorPair(color1, color2, colorPairs[i][0], colorPairs[i][1]) )
		{
			//printf("match!\n");
			nMatches++;
			playerNumber = i;
		}
	}
	//printf("\n");
	assert(nMatches <= 1); //You have a repeat color pair! you should not have more than (nColors)C(nPlayers)
	return playerNumber;

}

void moFlatlandColorPairFinderModule::imagePreprocess(IplImage *src){

	IplConvKernel *element = 0;//the pointer for morphological strucutre
	cvSmooth(src,src,CV_MEDIAN,5,0,0,0);//median filter, elliminate small noise

	//Then erode and dilate the image
	IplImage *tmp = cvCreateImage(cvGetSize(src),src->depth,src->nChannels);
	element = cvCreateStructuringElementEx(3,3,1,1,CV_SHAPE_RECT,0);//erode and dilate element

	//cvErode(src, tmp, element,1);//erode the image
	cvCopy(src,tmp);	
	cvDilate(tmp, src, element,5);//dilate the image
	cvReleaseImage(&tmp);

}


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
