import { ImageResponse } from 'next/og';
export const size = { width: 180, height: 180 };
export const contentType = 'image/png';
export default function AppleIcon(){return new ImageResponse(<div style={{width:'100%',height:'100%',background:'#092c49',display:'flex',alignItems:'center',justifyContent:'center',borderRadius:38}}><div style={{width:145,height:145,borderRadius:33,background:'#167a57',display:'flex',alignItems:'center',justifyContent:'center',fontSize:116,fontWeight:800,color:'white'}}>A</div></div>,size)}
