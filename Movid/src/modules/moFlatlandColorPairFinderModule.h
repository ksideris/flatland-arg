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

class moFlatlandColorPairFinderModule : public moImageFilterModule{
public:
	moFlatlandColorPairFinderModule();
	virtual ~moFlatlandColorPairFinderModule();
	
protected:

	int frameCounter;
	
	void clearBlobs();
	void applyFilter(IplImage*);
	
	void allocateBuffers();	

	CvMemStorage *storage;
	moDataGenericList *blobs;
	moDataGenericList *players;

	moDataStream *output_data;

	bool compareColorPair(int colorA1, int colorA2, int colorB1, int colorB2);
	int getPlayerIndex(int color1, int color2);

	void imagePreprocess(IplImage *src);
	int matchColor(int r, int g, int b);
	MODULE_INTERNALS();
};

#endif


