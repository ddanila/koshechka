#include "kitty.h"
#include <math.h>
#include <complex.h>
#include <string.h>

void speed(double t,int stop,double *v,double *dv) {
    if(!stop || t<=4){*v=.554;*dv=0;return;}
    if(t>=12){*v=0;*dv=0;return;}
    double a=PI*(t-4)/8;
    *v=.277*(1+cos(a)); *dv=-.277*PI/8*sin(a);
}
void initialize(Leg legs[4],double length) {
    const double states[4][4]={{.3,0,.554,0},{-.2,0,.554,0},{-.2,.22,-.45,-.1},{.3,.22,-.45,.1}};
    const double previous[4]={.554,.554,-.451,-.449};
    memset(legs,0,sizeof(Leg)*4);
    for(int i=0;i<4;i++){
        memcpy(legs[i].s,states[i],sizeof states[i]); legs[i].previous=previous[i];
        legs[i].front=i%2;legs[i].length=length;legs[i].branch=1;legs[i].landing=-1;
        if(i>=2){legs[i].k[1]=1./3;legs[i].k[2]=.6;}
    }
}
static void select_branch(Leg *l,double t,double v) {
    double x=l->s[0],y=l->s[1],dx=l->s[2],dy=l->s[3],*k=l->k;
    l->event=0;
    if(l->landing>=0 && t>=l->landing){y=0;dx=v;dy=0;l->landing=-1;l->event=3;}
    if(y<=0){
        dx=v;dy=0;y=0;
        l->branch=(fabs(x)<(l->front?.3:.4)||x<0||v==0)?1:2;
    }else{
        if(dx<=0 && l->previous>0){k[1]=dy/x;k[2]=fabs(x);k[3]=dy*dy/(2*y);l->event=1;}
        if(dx>=0 && l->previous<0){
            double duration=fabs(x)/2;
            k[3]=dy*dy/(2*y);k[4]=-v/y;k[5]=t;
            k[6]=(dy*duration+2*y)/pow(duration,3);
            k[7]=-(2*dy*duration+3*y)/pow(duration,2);
            l->landing=t+duration;l->event=2;
        }
        if(dx<=0)l->branch=fabs(x)<(l->front?.4:.3)?3:5;
        else l->branch=x<0?6:2;
    }
    l->s[0]=x;l->s[1]=y;l->s[2]=dx;l->s[3]=dy;
}
static void phases(Leg legs[4],double errors[4]) {
    double p[4],ss=0,cc=0;
    for(int i=0;i<4;i++){
        double a=sqrt(pow(legs[i].length,2)-H*H),x=legs[i].s[0];
        p[i]=legs[i].s[2]>=0?PI/2+PI*x/(2*a):3*PI/2-PI*x/(2*a);
        double offset=-i*PI/2;
        ss+=sin(p[i]-offset);cc+=cos(p[i]-offset);
    }
    double base=hypot(ss,cc)>1e-12?atan2(ss,cc):p[0];
    for(int i=0;i<4;i++){double e=p[i]-base-(-i*PI/2);errors[i]=atan2(sin(e),cos(e));}
}
static int derivative(Leg *l,const double s[4],double t,double error,int stop,double out[4]) {
    double x=s[0],y=s[1],dx=s[2],dy=s[3],v,dv,ax,ay,*k=l->k;
    speed(t,stop,&v,&dv);
    if(l->branch==1){ax=dv;ay=0;}
    else if(l->branch==2||l->branch==5){
        double gap=fabs(l->length-hypot(x,H-y));
        if(gap<1e-6){gap=1e-6;l->guards++;}
        ax=-x/gap;ay=l->branch==2?15*(H/8-y):k[1]*dx;
    }else if(l->branch==3){
        if(k[2]<=0)return 0;
        ax=-PI/k[2]*v*(1-error/(2*PI))*x;ay=k[1]*dx;
    }else if(l->branch==4){ax=0;ay=k[3];}
    else{ax=k[4]*dy+dv;ay=6*k[6]*(t-k[5])+2*k[7];}
    out[0]=dx;out[1]=dy;out[2]=ax;out[3]=ay;return 1;
}
int advance(Leg legs[4],double t,double dt,int stop,int coupling) {
    double v,dv,errors[4]={0};speed(t,stop,&v,&dv);
    for(int i=0;i<4;i++)select_branch(&legs[i],t,v);
    if(coupling)phases(legs,errors);
    for(int i=0;i<4;i++){
        Leg *l=&legs[i];double s[4],a[4],b[4],c[4],d[4],trial[4];
        memcpy(s,l->s,sizeof s);
        if(!derivative(l,s,t,errors[i],stop,a))return 0;
        for(int j=0;j<4;j++)trial[j]=s[j]+dt*a[j]/2;
        if(!derivative(l,trial,t+dt/2,errors[i],stop,b))return 0;
        for(int j=0;j<4;j++)trial[j]=s[j]+dt*b[j]/2;
        if(!derivative(l,trial,t+dt/2,errors[i],stop,c))return 0;
        for(int j=0;j<4;j++)trial[j]=s[j]+dt*c[j];
        if(!derivative(l,trial,t+dt,errors[i],stop,d))return 0;
        l->previous=s[2];
        for(int j=0;j<4;j++){
            l->s[j]=s[j]+dt*(a[j]+2*b[j]+2*c[j]+d[j])/6;
            if(!isfinite(l->s[j])||fabs(l->s[j])>=1e5)return 0;
        }
    }
    return 1;
}
static double complex vector(double gamma,double c,const double lengths[3]) {
    return lengths[0]*cexp(-I*c*gamma)+lengths[1]+lengths[2]*cexp(I*gamma);
}
int joints(double x,double y,int front,const double lengths[3],double foot,double d,double out[5][2]) {
    double c=front?.8:-1.2;double complex target=x+I*(fmax(0,y)-H);
    double rho=cabs(target),lo=0,hi=-1;
    for(int i=1;i<=32;i++){
        double candidate=PI*i/32;
        if(cabs(vector(-candidate,c,lengths))<=rho){hi=candidate;break;}
        lo=candidate;
    }
    if(rho>lengths[0]+lengths[1]+lengths[2]+1e-8||hi<0)return 0;
    for(int i=0;i<32;i++){
        double mid=(lo+hi)/2;
        if(cabs(vector(-mid,c,lengths))>rho)lo=mid;else hi=mid;
    }
    double gamma=-(lo+hi)/2,theta=carg(target)-carg(vector(gamma,c,lengths));
    double angles[3]={theta-c*gamma,theta,theta+gamma};double complex p=I*H;
    out[0][0]=0;out[0][1]=H;
    for(int i=0;i<3;i++){p+=lengths[i]*cexp(I*angles[i]);out[i+1][0]=creal(p);out[i+1][1]=cimag(p);}
    p-=foot*cexp(I*d*fmax(0,y));out[4][0]=creal(p);out[4][1]=cimag(p);return 1;
}
