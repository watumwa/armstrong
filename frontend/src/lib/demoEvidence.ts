/** Browser-only demonstration handoff; never store production medical, personal, or payment records here. */
export type DemoEvidence={id:string;facility:string;collector:string;location:string;submitted:string;waste:string;bags:number;weight:number;notes:string;status:'Pending review'|'Approved'|'Returned';reviewer?:string;reviewedAt?:string;reason?:string};
const KEY='armstrong-demo-evidence-v1';
export function readDemoEvidence():DemoEvidence[]{if(typeof window==='undefined')return [];try{const data=JSON.parse(localStorage.getItem(KEY)||'[]');return Array.isArray(data)?data.filter((v):v is DemoEvidence=>typeof v?.id==='string'&&typeof v?.facility==='string'&&typeof v?.status==='string'):[]}catch{return []}}
export function writeDemoEvidence(records:DemoEvidence[]){if(typeof window==='undefined')return;try{localStorage.setItem(KEY,JSON.stringify(records))}catch{/* Demo only: quota or privacy settings may prevent saving. */}}
export function upsertDemoEvidence(record:DemoEvidence){const existing=readDemoEvidence();writeDemoEvidence([record,...existing.filter(v=>v.id!==record.id)])}
