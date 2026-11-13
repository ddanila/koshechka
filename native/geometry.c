#include "kitty.h"
#include <math.h>
#include <string.h>

static double dot(const double a[3],const double b[3]){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
static void cross(const double a[3],const double b[3],double out[3]){
    out[0]=a[1]*b[2]-a[2]*b[1];out[1]=a[2]*b[0]-a[0]*b[2];out[2]=a[0]*b[1]-a[1]*b[0];
}
static void apply(const double r[3][3],const double v[3],double out[3]){
    for(int i=0;i<3;i++){out[i]=0;for(int j=0;j<3;j++)out[i]+=r[j][i]*v[j];}
}
static void solid(Node *n,const double a[2],const double b[2],double h0,double h1){
    double direction[3]={0,b[0]-a[0],b[1]-a[1]};
    double length=sqrt(dot(direction,direction));
    double u[3]={0,direction[1]/length,direction[2]/length};
    double psi=acos(fmax(-1,fmin(1,-u[2]))),omega=atan2(u[1],u[0]);
    /* Reconstruct the paper frame, rather than substituting a generic yaw. */
    double axis[3]={sin(psi)*cos(omega),sin(psi)*sin(omega),-cos(psi)};
    double z[3]={0,1,0};
    if(fabs(sin(psi))>1e-12){z[0]=cos(psi)*cos(omega);z[1]=cos(psi)*sin(omega);z[2]=sin(psi);}
    memcpy(n->r[0],axis,sizeof axis);cross(z,axis,n->r[1]);memcpy(n->r[2],z,sizeof z);
    n->o[0]=0;n->o[1]=a[0];n->o[2]=a[1];n->scale=length;
    n->dims[0]=h0/length;n->dims[1]=h1/length;n->dims[2]=h0/length;n->dims[3]=h1/length;
}
int pose(Leg legs[4],double t,int head_turn,Node nodes[NN],const double lengths[3],double foot,double d){
    const double thick[2][5]={{.18,.13,.075,.055,.04},{.135,.105,.065,.055,.04}};
    for(int i=0;i<4;i++){
        double points[5][2];if(!joints(legs[i].s[0],legs[i].s[1],i%2,lengths,foot,d,points))return 0;
        for(int j=0;j<NN;j++)if(nodes[j].leg==i&&nodes[j].segment>=0){
            int k=nodes[j].segment;solid(&nodes[j],points[k],points[k+1],thick[i%2][k],thick[i%2][k+1]);
        }
    }
    double q=head_turn?fmax(0,fmin(1,(t-9)/3)):0,turn=65*PI/180*(q*q*(3-2*q));
    for(int j=0;j<NN;j++)if(nodes[j].head){
        const double r[3][3]={{cos(turn),sin(turn),0},{-sin(turn),cos(turn),0},{0,0,1}};
        memcpy(nodes[j].r,r,sizeof r);
    }
    return 1;
}

/* The renderer keeps one primitive and a packed bitmap, not a polygon list. */
static uint8_t bitmap[2000];
static double view_angle,view_shift,view_span;
static int output_mode,frame_index,leaf_index;
static double turn(const double a[2],const double b[2],const double c[2]){
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);
}
static void raster(double p[8][2]){
    /* Insertion sort and monotone hull, at most 8 unique vertices. */
    for(int i=1;i<8;i++)for(int j=i;j>0&&(p[j][0]<p[j-1][0]||(p[j][0]==p[j-1][0]&&p[j][1]<p[j-1][1]));j--){
        double x=p[j][0],y=p[j][1];p[j][0]=p[j-1][0];p[j][1]=p[j-1][1];p[j-1][0]=x;p[j-1][1]=y;
    }
    double hull[16][2];int n=0;
    for(int i=0;i<8;i++){while(n>=2&&turn(hull[n-2],hull[n-1],p[i])<=0)n--;memcpy(hull[n++],p[i],sizeof p[i]);}
    int lower=n+1;
    for(int i=6;i>=0;i--){while(n>=lower&&turn(hull[n-2],hull[n-1],p[i])<=0)n--;memcpy(hull[n++],p[i],sizeof p[i]);}
    n--;if(n<3)return;
    /* Defined rule: include pixel centers on or inside every CCW edge. */
    for(int y=0;y<100;y++)for(int x=0;x<160;x++){
        double point[2]={x+.5,y+.5};int inside=1;
        for(int i=0;i<n;i++)if(turn(hull[i],hull[(i+1)%n],point)<-1e-10){inside=0;break;}
        if(inside){int bit=y*160+x;bitmap[bit/8]|=(uint8_t)(128>>(bit%8));}
    }
}
static void visit(Node nodes[NN],int index,const Transform *parent){
    Node *node=&nodes[index];Transform t;double offset[3];apply(parent->r,node->o,offset);
    for(int i=0;i<3;i++)t.o[i]=parent->o[i]+offset[i]*parent->scale;
    for(int j=0;j<3;j++)apply(parent->r,node->r[j],t.r[j]);
    t.scale=parent->scale*node->scale;
    if(node->leaf){
        double p[8][2];int vertex=0;
        for(int x=0;x<=1;x++)for(int corner=0;corner<4;corner++){
            const int signs[4][2]={{-1,-1},{-1,1},{1,1},{1,-1}};
            int sy=signs[corner][0],sz=signs[corner][1];
            double v[3]={x,sy*node->dims[x+2]/2,sz*node->dims[x]/2},world[3];apply(t.r,v,world);
            for(int j=0;j<3;j++)world[j]=t.o[j]+world[j]*t.scale;
            if(output_mode==2)printf("%d,%d,%d,%.17g,%.17g,%.17g\n",frame_index,leaf_index,vertex,world[0],world[1],world[2]);
            p[vertex][0]=80+(sin(view_angle)*world[0]+cos(view_angle)*world[1]+view_shift)*160/view_span;
            p[vertex][1]=82-world[2]*160/view_span;vertex++;
        }
        if(output_mode!=2)raster(p);
        leaf_index++;
    }else for(int j=index+1;j<NN;j++)if(nodes[j].parent==index)visit(nodes,j,&t);
}
void draw(Node nodes[NN],double angle,double shift,double span,int mode,int frame,int ink){
    const Transform identity={{0,0,0},{{1,0,0},{0,1,0},{0,0,1}},1};
    memset(bitmap,0,sizeof bitmap);view_angle=angle*PI/180;view_shift=shift;view_span=span;
    output_mode=mode;frame_index=frame;leaf_index=0;visit(nodes,0,&identity);
    if(mode==2)return;
    if(mode==3){printf("P4\n160 100\n");fwrite(bitmap,1,sizeof bitmap,stdout);return;}
    uint8_t row[120];printf("P4\n960 600\n");
    for(int y=0;y<600;y++){
        memset(row,0,sizeof row);
        for(int x=0;x<960;x++){
            int bit=(y/6)*160+x/6,inside=(bitmap[bit/8]&(128>>(bit%8)))!=0;
            int glyph=(y%6<5&&x%6%2==0&&x%6<5)||(y%6==4&&x%6<5);
            if(inside==ink&&glyph)row[x/8]|=(uint8_t)(128>>(x%8));
        }
        fwrite(row,1,sizeof row,stdout);
    }
}
