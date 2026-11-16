/* Optional genuine local LLM adapter. Model/runtime are a separate local bundle. */
(function(root){
  'use strict';
  const MODEL='Qwen2.5-0.5B-Instruct';
  function create(options={}){
    const base=new URL(options.baseUrl||'./local-ai/',typeof location!=='undefined'?location.href:'file:///');
    const browser=typeof location!=='undefined';
    if(base.username||base.password)throw new Error('Đường dẫn model không được chứa thông tin đăng nhập.');
    if(browser){
      if(!['http:','https:'].includes(location.protocol))throw new Error('Chat mô hình cần mở game qua localhost hoặc ứng dụng hỗ trợ tài nguyên cục bộ. Bản mở file vẫn có hướng dẫn viên ngoại tuyến.');
      if(base.origin!==location.origin)throw new Error('Chỉ cho phép model trong cùng ứng dụng, không tải model từ máy chủ ngoài.');
    }else if(base.protocol!=='file:'||base.hostname)throw new Error('Node chỉ dùng đường dẫn model cục bộ file://.');
    if(!base.pathname.endsWith('/'))base.pathname+='/';
    const runtimeUrl=new URL(options.runtimeModule||'runtime/transformers.min.js',base);
    if(runtimeUrl.username||runtimeUrl.password||(browser?(runtimeUrl.origin!==location.origin||!['http:','https:'].includes(runtimeUrl.protocol)):(runtimeUrl.protocol!=='file:'||runtimeUrl.hostname)))throw new Error('Runtime phải nằm trong cùng ứng dụng hoặc tệp cục bộ.');
    let modelPath;
    if(browser){
      const modelUrl=new URL(options.modelPath||'models/',base);
      if(modelUrl.username||modelUrl.password||modelUrl.origin!==location.origin||!['http:','https:'].includes(modelUrl.protocol))throw new Error('Đường dẫn model phải nằm trong cùng ứng dụng.');
      modelPath=modelUrl.href;
    }else{
      const nodeUrl=typeof require==='function'?require('node:url'):null;
      if(!nodeUrl)throw new Error('Node adapter cần được nạp bằng CommonJS require.');
      const modelUrl=options.modelPath?(String(options.modelPath).startsWith('file:')?new URL(options.modelPath):nodeUrl.pathToFileURL(String(options.modelPath))):new URL('models/',base);
      if(modelUrl.protocol!=='file:'||modelUrl.hostname)throw new Error('Node chỉ dùng model cục bộ.');
      // A URL string must not be mistaken for a native filename.
      if(options.modelPath&&/^[a-z][a-z0-9+.-]*:\/\//i.test(String(options.modelPath))&&!String(options.modelPath).startsWith('file:'))throw new Error('Node chỉ dùng model cục bộ.');
      modelPath=nodeUrl.fileURLToPath(modelUrl);
    }
    let generator=null,loading=null,busy=false,state='unloaded';
    async function load(onProgress){
      if(generator)return true;if(loading)return loading;
      state='loading';
      loading=(async()=>{
        const runtime=await import(runtimeUrl.href),env=runtime.env;
        env.allowRemoteModels=false;env.allowLocalModels=true;env.useBrowserCache=false;env.useFSCache=false;
        env.localModelPath=modelPath;
        if(env.backends?.onnx?.wasm){env.backends.onnx.wasm.wasmPaths=new URL('runtime/',base).href;env.backends.onnx.wasm.numThreads=1;env.backends.onnx.wasm.proxy=false;}
        generator=await runtime.pipeline('text-generation',MODEL,{dtype:'q8',device:options.device||(typeof location==='undefined'?'cpu':'wasm'),local_files_only:true,progress_callback:typeof onProgress==='function'?onProgress:undefined});
        state='ready';return true;
      })().catch(error=>{state='error';generator=null;throw error;}).finally(()=>{loading=null;});
      return loading;
    }
    async function chat(text,context={},history=[]){
      const question=String(text||'').trim().slice(0,800);if(!question)throw new Error('Hãy nhập câu hỏi.');
      if(busy)throw new Error('Mô hình đang trả lời câu trước.');
      if(!generator)throw new Error('Chưa nạp model cục bộ.');busy=true;
      try{
        const p=context.run?.player||context.player||{},run=context.run||{};
        const facts={hp:Number.isFinite(p.hp)?Math.ceil(p.hp):null,maxHp:Number.isFinite(p.maxHp)?p.maxHp:null,level:run.level||null,job:run.job?.name||null,map:run.map?.name||null,gold:context.save?.gold??null};
        const ruleEngine=root.MidgardAI||(typeof require==='function'?require('./ai.js'):null);
        const hint=ruleEngine?.chat(question,context);
        const grounding=hint&&!['unknown','capability'].includes(hint.intent)?' Gợi ý luật game đã kiểm tra: '+hint.text:'';
        const messages=[{role:'system',content:'Bạn là Ánh Dương, NPC đồng hành trong game sinh tồn Midgard, dùng mô hình Qwen chạy trên máy. Trả lời đúng câu hỏi bằng tiếng Việt, ngắn gọn trong một hoặc hai câu. Không bịa rằng bạn đã thay đổi vật phẩm, chỉ số hoặc save. Nếu không biết tính năng, nói chưa rõ. Dữ liệu tình huống hiện tại: '+JSON.stringify(facts)+grounding}];
        for(const item of history.slice(-4))if(['user','assistant'].includes(item?.role)&&typeof item.content==='string')messages.push({role:item.role,content:item.content.slice(0,800)});
        messages.push({role:'user',content:question});
        const maxTokens=Math.max(8,Math.min(128,Number.isFinite(options.maxNewTokens)?Math.floor(options.maxNewTokens):96));
        const output=await generator(messages,{max_new_tokens:maxTokens,do_sample:false,repetition_penalty:1.08,return_full_text:false});
        const generated=output?.[0]?.generated_text;
        const answer=typeof generated==='string'?generated:Array.isArray(generated)?generated.filter(x=>x.role==='assistant').at(-1)?.content:null;
        if(typeof answer!=='string'||!answer.trim())throw new Error('Mô hình không trả về văn bản hợp lệ.');
        return {text:answer.trim(),mode:'local-llm',model:MODEL};
      }finally{busy=false;}
    }
    async function dispose(){if(busy||loading)throw new Error('Chờ mô hình hoàn tất trước khi giải phóng.');if(generator)await generator.dispose();generator=null;state='unloaded';}
    return {load,chat,dispose,get status(){return {state,busy,model:MODEL,offline:true};}};
  }
  const api={create,MODEL};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.MidgardLLM=api;
})(typeof globalThis!=='undefined'?globalThis:this);
