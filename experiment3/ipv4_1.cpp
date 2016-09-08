/*
* THIS FILE IS FOR IP TEST
*/
// system support
#include "sysInclude.h"

extern void ip_DiscardPkt(char* pBuffer,int type);

extern void ip_SendtoLower(char*pBuffer,int length);

extern void ip_SendtoUp(char *pBuffer,int length);

extern unsigned int getIpv4Address();

// implemented by students

SHORT calChecksum(USHORT *buffer,int len){    // 计算校验和 
	unsigned long sum = 0;    // 四个字节以容纳进位
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
	while (sum>>16){
		sum = (sum>>16) + (sum & 0xffff);
	}
	return (USHORT)(~sum);    // 取反
}

int stud_ip_recv(char *pBuffer,unsigned short length)
{
	// char 占一个字节，一次索引取出8位，version 和 ihl 一起取出，需要按位处理，留下需要的
	// 判断version 是否正确：4
	if((pBuffer[0] & 0xf0) != 0x40){    // 取高四位
		ip_DiscardPkt(pBuffer,STUD_IP_TEST_VERSION_ERROR);
		return 1;
	}
	// 判断IHL是否正确：5
	if((pBuffer[0] & 0x0f) != 0x05){    // 取低四位
		ip_DiscardPkt(pBuffer,STUD_IP_TEST_HEADLEN_ERROR);
		return 1;
	}
	// 判断TTL是否为0，若是，丢弃
	if(pBuffer[8] == 0x00){    // ttl占一个字节，所引可直接取出
		ip_DiscardPkt(pBuffer,STUD_IP_TEST_TTL_ERROR);
		return 1;
	}
	// 判断头校验和是否正确：为0
	SHORT sum = calChecksum((USHORT *)pBuffer,length);
	if(sum != 0){
		ip_DiscardPkt(pBuffer,STUD_IP_TEST_CHECKSUM_ERROR);
		return 1;
	}
	// 目的地址是否正确：与本机地址相同
	unsigned int address = getIpv4Address();    // 本机ipv4地址
	char *tempAddress = pBuffer + 16;    // ipv4分组头中，目的地址（占4个字节）的起始位置
	unsigned int *intAddress = (unsigned int *)tempAddress;    // 取4个字节
	if(address != ntohl(*intAddress)){
		ip_DiscardPkt(pBuffer,STUD_IP_TEST_DESTINATION_ERROR);
		return 1;
	}
	ip_SendtoUp(pBuffer,length);    // 发送
	return 0;
}

int stud_ip_Upsend(char *pBuffer,unsigned short len,unsigned int srcAddr,
				   unsigned int dstAddr,byte protocol,byte ttl)
{
	byte *datagram = new byte[20 + len];    // 申请空间，加上头部 20字节
	datagram[0] = 0x45;    // version=4；IHL=5；
	datagram[1] = 0x80;    // Type of service = 0x800;
	// 总长度
	byte *dag_hl = datagram + 2;    // 总长度起始位置
	unsigned short int *length = (unsigned short int *)dag_hl;    // 总长度占两个字节，扩充
	*length = htons(20 + len);
	// 标识：两个字节
	datagram[4] = 0x00;
	datagram[5] = 0x00;
	// 标志位和片偏移：两个字节
	datagram[6] = 0x00;
	datagram[7] = 0x00;

	datagram[8] = ttl;
	datagram[9] = protocol;
	// 首部校验和：两个字节，计算前置零
	datagram[10] = 0x00;
	datagram[11] = 0x00;
	// 源地址
	byte *dag_srcAddr = datagram + 12;    // 源地址起始位置
	unsigned int *srcAddrTemp = (unsigned int *)dag_srcAddr;    // 源地址占四个字节，扩充
	*srcAddrTemp = ntohl(srcAddr);
	// 目的地址
	byte *dag_dstAddr = datagram + 16;    // 目的地址起始位置
	unsigned int *dstAddrTemp = (unsigned int *)dag_dstAddr;    // 目的地址占四个字节，扩充
	*dstAddrTemp = ntohl(dstAddr);
	// 最后计算首部校验和
	byte *dag_checksum = datagram + 10;    // 校验和起始位置
	short int *headerChecksum = (short int *)dag_checksum;    // 校验和占四个字节，扩充
	*headerChecksum = calChecksum((USHORT *)datagram,20);
	// 封装上层传来的 segment
	for(int i = 0; i < len; i ++){
		 datagram[i + 20] = pBuffer[i];
	}
	// 传递给下层
	ip_SendtoLower(datagram,20 + len);
	return 0;
}
