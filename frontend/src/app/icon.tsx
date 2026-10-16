import { ImageResponse } from 'next/og';
export const size = { width: 512, height: 512 };
export const contentType = 'image/png';
export default function Icon(){return new ImageResponse(<div style={{width:'100%',height:'100%',background:'#092c49',display:'flex',alignItems:'center',justifyContent:'center',borderRadius:100}}><div style={{display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',width:385,height:385,borderRadius:90,background:'#167a57',color:'white'}}><div style={{fontSize:230,fontWeight:800,lineHeight:1}}>A</div><div style={{fontSize:30,fontWeight:700,letterSpacing:5}}>GLOBAL</div></div></div>,size)}
