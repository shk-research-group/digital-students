const { PromptTemplate } = require('@langchain/core/prompts');
const { ToolMessage, AIMessageChunk, AIMessage } = require('@langchain/core/messages');

const inputObj = $input.item.json;
var query = inputObj.question;
const prompt = PromptTemplate.fromTemplate(query);

function needToRetryModel(content) {
  return content.startsWith("<function") || content.includes("function>") || content.includes("<brave_search")
}

const llms = await this.getInputConnectionData('ai_languageModel', 0);
console.log(llms);
var gptLlm = null;
var groqLlm = null;
for (const llm of llms) {
  if(llm.model.includes("gpt")) {
    gptLlm = llm;
  } else {
    groqLlm = llm;
  }
}

const tools = await this.getInputConnectionData('ai_tool', 0);
var gptLlmWithTools = groqLlm.bindTools(tools);
console.log(gptLlmWithTools);
//let chain = prompt.pipe(gptLlm);
const originalMessages = [
  {
    role: "system",
    content: "You are a helpful AI assistant."
  },
  {
    role: "user",
    content: query
  }
];
var output = await gptLlmWithTools.invoke(originalMessages);
if (!output.tool_calls || output.tool_calls.length == 0) {
  return [ {
  output: output.content
} ]
}
if (needToRetryModel(output.content)) {
  for (let idx = 0; idx < 3; idx++)  {
    // Need to retry until getting correct response
    output = await gptLlmWithTools.invoke(originalMessages);
  
    if (!output.tool_calls || output.tool_calls.length == 0) {
      return [ {
      output: output.content
    } ]
    } else if (!needToRetryModel(output.content)) {
      break;
    }
  }
  if (needToRetryModel(output.content)) {
    return [
      {
        output: "Got error on trying to answer"
      }
    ]
  }
}
originalMessages.push(output);
console.log(output.tool_calls[0].args);
const result = await tools[0].func(output.tool_calls[0].args.query);
console.log(result);
const tm = new ToolMessage(result, output.tool_calls[0].id);
originalMessages.push(tm);
//const aiMessage = new AIMessageChunk();
//originalMessages.push(aiMessage);
const final = await gptLlmWithTools.invoke(originalMessages);
console.log(final);
return [ {
  output: final.content
} ];