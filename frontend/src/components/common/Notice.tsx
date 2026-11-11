export function Notice({message,retry}:{message:string;retry?:()=>void}){return message?<div role="alert" className="notice">{message}{retry&&<button onClick={retry}>重新载入</button>}</div>:null}
