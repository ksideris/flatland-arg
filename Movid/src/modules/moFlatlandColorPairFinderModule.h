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


#ifndef MO_FLATLANDCOLORPAIRFINDER_MODULE_H
#define MO_FLATLANDCOLORPAIRFINDER_MODULE_H

#include "moImageFilterModule.h"
#include "../moDataGenericContainer.h"
#include <math.h>

struct ColoredPt // Storage for the blobs
{
        double red;
        double green;
        double blue;
	double x;
	double y;
	int color;
};
struct Player // Storage for the players
{
        ColoredPt point1;
	ColoredPt point2;
	double x;
	double y;
	int id;
	bool updated;
};

class moFlatlandColorPairFinderModule : public moImageFilterModule{
public:
	moFlatlandColorPairFinderModule();
	virtual ~moFlatlandColorPairFinderModule();
	
protected:

	int frameCounter;
	
	void clearBlobs();
	void applyFilter(IplImage*);
	
	void allocateBuffers();	
	bool initialized;
	std::vector<Player> Players;	
	CvMemStorage *storage;
	moDataGenericList *blobs;
	moDataGenericList *players;

	moDataStream *output_data;
	
	
	bool compareColorPair(int colorA1, int colorA2, int colorB1, int colorB2);
	int getPlayerIndex(ColoredPt color1, ColoredPt color2, double avX,double avY,bool init);
	int FindPairs(std::vector<ColoredPt> cPts,bool init);
	void MatchPlayers(int *pairs,std::vector<ColoredPt> cPts,bool init);
	//void MatchPlayers(int *pairs,std::vector<ColoredPt> cPts);
	void imagePreprocess(IplImage *src);
	int matchColor(int r, int g, int b);
	MODULE_INTERNALS();
};

#endif


