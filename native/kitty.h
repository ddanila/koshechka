#ifndef KITTY_H
#define KITTY_H
#include <stdio.h>
#include <stdint.h>
#define PI 3.14159265358979323846
#define H .75
#define NN 36
/* State and workspaces have fixed size, independent of movie duration. */
typedef struct { double s[4], k[8], previous, length, landing; int front, branch, event, guards; } Leg;
typedef struct { double o[3], r[3][3], scale, dims[4]; int parent, leaf, leg, segment, head; } Node;
typedef struct { double o[3], r[3][3], scale; } Transform;
void speed(double t,int stop,double *v,double *dv);
void initialize(Leg legs[4],double length);
int advance(Leg legs[4],double t,double dt,int stop,int coupling);
int joints(double x,double y,int front,const double lengths[3],double foot,double d,double out[5][2]);
int pose(Leg legs[4],double t,int head_turn,Node nodes[NN],const double lengths[3],double foot,double d);
void draw(Node nodes[NN],double angle,double shift,double span,int mode,int frame,int ink);
#endif
