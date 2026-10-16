import {NextResponse,type NextRequest} from 'next/server';
import {jwtVerify} from 'jose';
export async function middleware(request:NextRequest){const path=request.nextUrl.pathname;if(path==='/login')return NextResponse.next();const token=request.cookies.get('armstrong_session')?.value;const secret=process.env.AUTH_SECRET;let valid=false;try{if(token&&secret&&secret.length>=32){await jwtVerify(token,new TextEncoder().encode(secret));valid=true}}catch{}if(!valid)return NextResponse.redirect(new URL('/login',request.url));return NextResponse.next()}
export const config={runtime:'nodejs',matcher:['/','/collector/:path*','/verification/:path*','/schedules/:path*','/qr-registry/:path*','/agreements/:path*','/users/:path*','/maps/:path*']};
