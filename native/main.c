#include "kitty.h"
#include "presets.h"
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <errno.h>

static double number(const char *s){char *end;errno=0;double v=strtod(s,&end);if(errno||*end||end==s||!isfinite(v)){fprintf(stderr,"Invalid number: %s\n",s);exit(2);}return v;}
int main(int argc,char **argv){
    double duration=16,dt=.001,fps=24,angle=fitted_angle;
    const Node *template=fitted_nodes;const double *lengths=fitted_lengths;
    double foot=fitted_foot,d=fitted_d,preset_angle=fitted_angle;int angle_set=0;
    int stop=1,coupling=1,head=1,follow=1,ink=0,mode=0;
    for(int i=1;i<argc;i++){
        if(!strcmp(argv[i],"--cruise"))stop=0;
        else if(!strcmp(argv[i],"--no-coupling"))coupling=0;
        else if(!strcmp(argv[i],"--no-head-turn"))head=0;
        else if(!strcmp(argv[i],"--fixed-camera"))follow=0;
        else if(!strcmp(argv[i],"--ink"))ink=1;
        else if(!strcmp(argv[i],"--trace"))mode=1;
        else if(!strcmp(argv[i],"--vertices"))mode=2;
        else if(!strcmp(argv[i],"--mask"))mode=3;
        else if(!strcmp(argv[i],"--events"))mode=4;
        else if(!strcmp(argv[i],"--memory")){printf("{\"leg_bytes\":%zu,\"nodes_bytes\":%zu,\"transform_bytes\":%zu,\"bitmap_bytes\":2000,\"output_row_bytes\":120}\n",sizeof(Leg)*4,sizeof(Node)*NN,sizeof(Transform));return 0;}
        else if(!strcmp(argv[i],"--help")){puts("kitty [--duration N] [--fps N] [--dt N] [--angle N] [--preset baseline|fitted] [--cruise] [--no-coupling] [--no-head-turn] [--fixed-camera] [--ink] [--trace|--vertices|--mask|--events|--memory]\nDefault output: concatenated 960x600 PBM character frames. No heap or frame history.");return 0;}
        else if(i+1<argc){
            const char *arg=argv[i],*value=argv[++i];
            if(!strcmp(arg,"--duration"))duration=number(value);
            else if(!strcmp(arg,"--fps"))fps=number(value);
            else if(!strcmp(arg,"--dt"))dt=number(value);
            else if(!strcmp(arg,"--angle")){angle=number(value);angle_set=1;}
            else if(!strcmp(arg,"--preset")&&!strcmp(value,"baseline")){
                template=baseline_nodes;lengths=baseline_lengths;foot=baseline_foot;d=baseline_d;preset_angle=baseline_angle;
            }else if(!strcmp(arg,"--preset")&&!strcmp(value,"fitted")){
                template=fitted_nodes;lengths=fitted_lengths;foot=fitted_foot;d=fitted_d;preset_angle=fitted_angle;
            }
            else{fprintf(stderr,"Unknown option or preset: %s %s\n",arg,value);return 2;}
        }else{fprintf(stderr,"Missing value or unknown option: %s\n",argv[i]);return 2;}
    }
    if(duration<=0||duration>120||fps<1||fps>120||fps!=floor(fps)||dt<=0||dt>.02){fputs("Invalid duration, fps or dt\n",stderr);return 2;}
    Leg legs[4];Node nodes[NN];memcpy(nodes,template,sizeof nodes);
    if(!angle_set)angle=preset_angle;
    initialize(legs,lengths[0]+lengths[1]+lengths[2]);
    double t=0,distance=0;
    /* Same frame-aligned trapezoid integral as Python, needed by fixed camera. */
    double total=0,clock=0;
    int frames=(int)nearbyint(duration*fps);
    for(int frame=0;frame<=frames;frame++)while(clock<frame/fps-1e-12){
        double delta=fmin(dt,frame/fps-clock),v0,v1,dv;speed(clock,stop,&v0,&dv);speed(clock+delta,stop,&v1,&dv);total+=delta*(v0+v1)/2;clock+=delta;
    }
    if(mode==1)puts("frame,t,distance,leg,x,y,dx,dy,branch,k1,k2,k3,k4,k5,k6,k7");
    if(mode==2)puts("frame,solid,vertex,x,y,z");
    if(mode==4)puts("t,leg,event");
    for(int frame=0;frame<=frames;frame++){
        double target=frame/fps;
        while(t<target-1e-12){
            double delta=fmin(dt,target-t),v0,v1,dv;speed(t,stop,&v0,&dv);
            if(!advance(legs,t,delta,stop,coupling)){fputs("Unstable trajectory\n",stderr);return 1;}
            if(mode==4)for(int i=0;i<4;i++)if(legs[i].event)printf("%.17g,%d,%d\n",t,i,legs[i].event);
            speed(t+delta,stop,&v1,&dv);distance+=delta*(v0+v1)/2;t+=delta;
        }
        if(mode==1){for(int i=0;i<4;i++){
            printf("%d,%.17g,%.17g,%d",frame,target,distance,i);
            for(int j=0;j<4;j++)printf(",%.17g",legs[i].s[j]);
            printf(",%d",legs[i].branch);
            for(int j=1;j<=7;j++)printf(",%.17g",legs[i].k[j]);
            putchar('\n');
        }}else if(mode!=4){
            if(!pose(legs,target,head,nodes,lengths,foot,d)){fputs("Unreachable leg\n",stderr);return 1;}
            draw(nodes,angle,follow?0:total/2-distance,follow?5.2:9,mode,frame,ink);
        }
    }
    return ferror(stdout)?1:0;
}
