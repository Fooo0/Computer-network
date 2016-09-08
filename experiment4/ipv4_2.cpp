/*
* THIS FILE IS FOR IP FORWARD TEST
*/
#include "sysInclude.h"

/*采用二叉树结点作为路由表表项*/
typedef struct stu_table_record{
	unsigned int dest;		//目标地址
	unsigned int masklen;	//掩码长度
	unsigned int nexthop;		//下一跳地址
	struct stu_table_record *lrecord;	//左子树(小)
	struct stu_table_record *rrecord;	//右子树(大)
}stu_table_record;

// system support
extern void fwd_LocalRcv(char *pBuffer, int length);

extern void fwd_SendtoLower(char *pBuffer, int length, unsigned int nexthop);

extern void fwd_DiscardPkt(char *pBuffer, int type);

extern unsigned int getIpv4Address( );

stu_table_record *stu_fwardtable = NULL;    // 二叉树的根
// implemented by students

void stud_Route_Init(){
	if((stu_fwardtable = (stu_table_record*)malloc(sizeof(stu_table_record))))
	{
		stu_fwardtable->dest = 0;
		stu_fwardtable->masklen = 0;
		stu_fwardtable->nexthop = 0;
		stu_fwardtable->lrecord = NULL;
		stu_fwardtable->rrecord = NULL;
	}
	else
	{
		printf("Init failed.\n");
		exit(0);
	}
	return;
}

void stud_route_add(stud_route_msg *proute){
	stu_table_record *tmp = stu_fwardtable;
	unsigned int masklen=ntohl(proute->masklen);
	unsigned int dest=ntohl(proute->dest);
	unsigned int record_dest=dest>>(32-masklen)<<(32-masklen);    // 记录目标地址的网络地址,移位使低位置0
	unsigned int nexthop=proute->nexthop;
	
	if(tmp->dest == 0 && tmp->masklen == 0 && tmp->nexthop == 0)    // 没有任何记录
	{
		tmp->dest = record_dest;
		tmp->masklen = masklen;
		tmp->nexthop = nexthop;
	}
	else
	{
		stu_table_record *last = tmp;    // 上一个结点，新节点插入其左/右
		int to_left = 1;    // 左子:1,右子:0.
		
		while(tmp)
		{
			if(tmp->dest < record_dest)    // 新结点更大,继续向右搜索
			{
				last = tmp;
				to_left = 0;
				tmp = tmp->rrecord;
			}
			else if(tmp->dest > record_dest)    // 新结点更小,继续向左搜索
			{
				last = tmp;
				to_left = 1;
				tmp = tmp->lrecord;
			}
			else    // 找到与新结点相同的，无需更新 
			{
				return;
			}
		}
		
		if((tmp = (stu_table_record*)malloc(sizeof(stu_table_record))))
		{
			// 添加相关信息
			tmp->dest = record_dest;
			tmp->masklen = masklen;
			tmp->nexthop = nexthop;
			tmp->lrecord = NULL;
			tmp->rrecord = NULL;
			// 插入到对应位置
			if(to_left)
			{
				last->lrecord = tmp;
			}
			else
			{
				last->rrecord = tmp;
			}
		}
		else
		{
			printf("Update failed.\n");
			exit(0);
		}
	}
	return;
}

SHORT calChecksum(USHORT *buffer,int len){    // 计算校验和 
	int sum = 0;    // 四个字节以容纳进位
	// 防止两个字节两个字节相加后，结尾剩一个字节出错
	while(len > 1){
		sum += *buffer ++;    // 16位，两个字节两个字节相加
		len -= sizeof(USHORT);
	}
	// 加剩下的一个字节
	if(len){
		sum += *(UCHAR *)buffer;
	}
	// 回卷
	while(sum>>16){
		sum = sum>>16 + sum<<16>>16;
	}
	return (USHORT)(~sum);    // 取反
}

unsigned int get_nexthop(unsigned int dest){//查找下一跳
	stu_table_record *tmp = stu_fwardtable;
	unsigned int nexthop = 0;

	while(tmp){    // 比较目标地址和路由表中的地址之间的关系
		if(tmp->dest == dest>>(32-tmp->masklen)<<(32-tmp->masklen)){    // 找到相应的路由项
			nexthop = tmp->nexthop;
			tmp = tmp->rrecord;    // 寻找最长匹配
		}
		else if(tmp->dest < dest>>(32-tmp->masklen)<<(32-tmp->masklen)){
			tmp = tmp->lrecord;
		}
		else{
			tmp = tmp->rrecord;
		}
	}
	return nexthop;
}

int stud_fwd_deal(char *pBuffer, int length){
	// 判断TTL是否为0，若是，丢弃
	if(pBuffer[8] == 0x00){    // ttl占一个字节，所引可直接取出
		fwd_DiscardPkt(pBuffer, STUD_FORWARD_TEST_TTLERROR);	
		return 1;
	}

	// 是否发给本机
	unsigned int address = getIpv4Address();    // 本机ipv4地址
	char *tempAddress = pBuffer + 16;    // ipv4分组头中，目的地址（占4个字节）的起始位置
	unsigned int *intAddress = (unsigned int *)tempAddress;    // 取4个字节
	unsigned int dest = ntohl(*intAddress);
	if(address == dest){
		fwd_LocalRcv(pBuffer, length);
		return 0;
	}
	
	unsigned int nexthop = get_nexthop(dest);
	if(nexthop == 0){    // 没有表项
		fwd_DiscardPkt(pBuffer, STUD_FORWARD_TEST_NOROUTE);
		return 1;
	}

	pBuffer[8] --;    // TTL - 1

	// 重新计算校验和
	char *tempchecksum = pBuffer + 10;    // ipv4分组头中，checksum（占2个字节）的起始位置
	short int *checksum = (short int *)tempchecksum;    // 取2个字节
	*checksum = 0;    // 先置零
	*checksum = calChecksum((USHORT *)pBuffer, 20);    // 计算校验和

	/*转发*/
	fwd_SendtoLower(pBuffer, length, nexthop);
	return 0;
}
