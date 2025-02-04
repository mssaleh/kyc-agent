# Assistants API overview

===============================

Build AI Assistants with essential tools and integrations.

The Assistants API allows you to build AI assistants within your own applications. An Assistant has instructions and can leverage models, tools, and files to respond to user queries. The Assistants API currently supports three types of [tools](/docs/assistants/tools): Code Interpreter, File Search, and Function calling.

You can explore the capabilities of the Assistants API using the [Assistants playground](/playground?mode=assistant) or by building a step-by-step integration outlined in our [Assistants API quickstart](/docs/assistants/quickstart).

How Assistants work
-------------------

The Assistants API is designed to help developers build powerful AI assistants capable of performing a variety of tasks.

The Assistants API is in **beta** and we are actively working on adding more functionality. Share your feedback in our [Developer Forum](https://community.openai.com/)!

1.  Assistants can call OpenAI’s **[models](/docs/models)** with specific instructions to tune their personality and capabilities.
2.  Assistants can access **multiple tools in parallel**. These can be both OpenAI-hosted tools — like [code\_interpreter](/docs/assistants/tools/code-interpreter) and [file\_search](/docs/assistants/tools/file-search) — or tools you build / host (via [function calling](/docs/assistants/tools/function-calling)).
3.  Assistants can access **persistent Threads**. Threads simplify AI application development by storing message history and truncating it when the conversation gets too long for the model’s context length. You create a Thread once, and simply append Messages to it as your users reply.
4.  Assistants can access files in several formats — either as part of their creation or as part of Threads between Assistants and users. When using tools, Assistants can also create files (e.g., images, spreadsheets, etc) and cite files they reference in the Messages they create.

Objects
-------

![Assistants object architecture diagram](https://cdn.openai.com/API/docs/images/diagram-assistant.webp)

|Object|What it represents|
|---|---|
|Assistant|Purpose-built AI that uses OpenAI’s models and calls tools|
|Thread|A conversation session between an Assistant and a user. Threads store Messages and automatically handle truncation to fit content into a model’s context.|
|Message|A message created by an Assistant or a user. Messages can include text, images, and other files. Messages stored as a list on the Thread.|
|Run|An invocation of an Assistant on a Thread. The Assistant uses its configuration and the Thread’s Messages to perform tasks by calling models and tools. As part of a Run, the Assistant appends Messages to the Thread.|
|Run Step|A detailed list of steps the Assistant took as part of a Run. An Assistant can call tools or create Messages during its run. Examining Run Steps allows you to introspect how the Assistant is getting to its final results.|

# Assistants API quickstart

=================================

Step-by-step guide to creating an assistant.

A typical integration of the Assistants API has the following flow:

1.  Create an [Assistant](/docs/api-reference/assistants/createAssistant) by defining its custom instructions and picking a model. If helpful, add files and enable tools like Code Interpreter, File Search, and Function calling.
2.  Create a [Thread](/docs/api-reference/threads) when a user starts a conversation.
3.  Add [Messages](/docs/api-reference/messages) to the Thread as the user asks questions.
4.  [Run](/docs/api-reference/runs) the Assistant on the Thread to generate a response by calling the model and the tools.

This starter guide walks through the key steps to create and run an Assistant that uses [Code Interpreter](/docs/assistants/tools/code-interpreter). In this example, we're [creating an Assistant](/docs/api-reference/assistants/createAssistant) that is a personal math tutor, with the Code Interpreter tool enabled.

Calls to the Assistants API require that you pass a beta HTTP header. This is handled automatically if you’re using OpenAI’s official Python or Node.js SDKs. `OpenAI-Beta: assistants=v2`

Step 1: Create an Assistant
---------------------------

An [Assistant](/docs/api-reference/assistants/object) represents an entity that can be configured to respond to a user's messages using several parameters like `model`, `instructions`, and `tools`.

Create an Assistant

```python
from openai import OpenAI
client = OpenAI()

assistant = client.beta.assistants.create(
  name="Math Tutor",
  instructions="You are a personal math tutor. Write and run code to answer math questions.",
  tools=[{"type": "code_interpreter"}],
  model="gpt-4o",
)
```

```javascript
import OpenAI from "openai";
const openai = new OpenAI();

async function main() {
  const assistant = await openai.beta.assistants.create({
    name: "Math Tutor",
    instructions: "You are a personal math tutor. Write and run code to answer math questions.",
    tools: [{ type: "code_interpreter" }],
    model: "gpt-4o"
  });
}

main();
```

```bash
curl "https://api.openai.com/v1/assistants" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "OpenAI-Beta: assistants=v2" \
  -d '{
    "instructions": "You are a personal math tutor. Write and run code to answer math questions.",
    "name": "Math Tutor",
    "tools": [{"type": "code_interpreter"}],
    "model": "gpt-4o"
  }'
```

Step 2: Create a Thread
-----------------------

A [Thread](/docs/api-reference/threads/object) represents a conversation between a user and one or many Assistants. You can create a Thread when a user (or your AI application) starts a conversation with your Assistant.

Create a Thread

```python
thread = client.beta.threads.create()
```

```javascript
const thread = await openai.beta.threads.create();
```

```bash
curl https://api.openai.com/v1/threads \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "OpenAI-Beta: assistants=v2" \
  -d ''
```

Step 3: Add a Message to the Thread
-----------------------------------

The contents of the messages your users or applications create are added as [Message](/docs/api-reference/messages/object) objects to the Thread. Messages can contain both text and files. There is a limit of 100,000 Messages per Thread and we smartly truncate any context that does not fit into the model's context window.

Add a Message to the Thread

```python
message = client.beta.threads.messages.create(
  thread_id=thread.id,
  role="user",
  content="I need to solve the equation `3x + 11 = 14`. Can you help me?"
)
```

```javascript
const message = await openai.beta.threads.messages.create(
  thread.id,
  {
    role: "user",
    content: "I need to solve the equation `3x + 11 = 14`. Can you help me?"
  }
);
```

```bash
curl https://api.openai.com/v1/threads/thread_abc123/messages \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "OpenAI-Beta: assistants=v2" \
  -d '{
      "role": "user",
      "content": "I need to solve the equation `3x + 11 = 14`. Can you help me?"
    }'
```

Step 4: Create a Run
--------------------

Once all the user Messages have been added to the Thread, you can [Run](/docs/api-reference/runs/object) the Thread with any Assistant. Creating a Run uses the model and tools associated with the Assistant to generate a response. These responses are added to the Thread as `assistant` Messages.

With streaming

You can use the 'create and stream' helpers in the Python and Node SDKs to create a run and stream the response.

Create and Stream a Run

```python
from typing_extensions import override
from openai import AssistantEventHandler
 
# First, we create a EventHandler class to define
# how we want to handle the events in the response stream.
 
class EventHandler(AssistantEventHandler):    
  @override
  def on_text_created(self, text) -> None:
    print(f"\nassistant > ", end="", flush=True)
      
  @override
  def on_text_delta(self, delta, snapshot):
    print(delta.value, end="", flush=True)
      
  def on_tool_call_created(self, tool_call):
    print(f"\nassistant > {tool_call.type}\n", flush=True)
  
  def on_tool_call_delta(self, delta, snapshot):
    if delta.type == 'code_interpreter':
      if delta.code_interpreter.input:
        print(delta.code_interpreter.input, end="", flush=True)
      if delta.code_interpreter.outputs:
        print(f"\n\noutput >", flush=True)
        for output in delta.code_interpreter.outputs:
          if output.type == "logs":
            print(f"\n{output.logs}", flush=True)
 
# Then, we use the `stream` SDK helper 
# with the `EventHandler` class to create the Run 
# and stream the response.
 
with client.beta.threads.runs.stream(
  thread_id=thread.id,
  assistant_id=assistant.id,
  instructions="Please address the user as Jane Doe. The user has a premium account.",
  event_handler=EventHandler(),
) as stream:
  stream.until_done()
```

```javascript
// We use the stream SDK helper to create a run with
// streaming. The SDK provides helpful event listeners to handle 
// the streamed response.
 
const run = openai.beta.threads.runs.stream(thread.id, {
    assistant_id: assistant.id
  })
    .on('textCreated', (text) => process.stdout.write('\nassistant > '))
    .on('textDelta', (textDelta, snapshot) => process.stdout.write(textDelta.value))
    .on('toolCallCreated', (toolCall) => process.stdout.write(`\nassistant > ${toolCall.type}\n\n`))
    .on('toolCallDelta', (toolCallDelta, snapshot) => {
      if (toolCallDelta.type === 'code_interpreter') {
        if (toolCallDelta.code_interpreter.input) {
          process.stdout.write(toolCallDelta.code_interpreter.input);
        }
        if (toolCallDelta.code_interpreter.outputs) {
          process.stdout.write("\noutput >\n");
          toolCallDelta.code_interpreter.outputs.forEach(output => {
            if (output.type === "logs") {
              process.stdout.write(`\n${output.logs}\n`);
            }
          });
        }
      }
    });
```

See the full list of Assistants streaming events in our API reference [here](/docs/api-reference/assistants-streaming/events). You can also see a list of SDK event listeners for these events in the [Python](https://github.com/openai/openai-python/blob/main/helpers.md#assistant-events) & [Node](https://github.com/openai/openai-node/blob/master/helpers.md#assistant-events) repository documentation.

Without streaming

Runs are asynchronous, which means you'll want to monitor their `status` by polling the Run object until a [terminal status](/docs/assistants/deep-dive#runs-and-run-steps) is reached. For convenience, the 'create and poll' SDK helpers assist both in creating the run and then polling for its completion.

Create a Run

```python
run = client.beta.threads.runs.create_and_poll(
  thread_id=thread.id,
  assistant_id=assistant.id,
  instructions="Please address the user as Jane Doe. The user has a premium account."
)
```

```javascript
let run = await openai.beta.threads.runs.createAndPoll(
  thread.id,
  { 
    assistant_id: assistant.id,
    instructions: "Please address the user as Jane Doe. The user has a premium account."
  }
);
```

```bash
curl https://api.openai.com/v1/threads/thread_abc123/runs \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -H "OpenAI-Beta: assistants=v2" \
  -d '{
    "assistant_id": "asst_abc123",
    "instructions": "Please address the user as Jane Doe. The user has a premium account."
  }'
```

Once the Run completes, you can [list the Messages](/docs/api-reference/messages/listMessages) added to the Thread by the Assistant.

```python
if run.status == 'completed': 
  messages = client.beta.threads.messages.list(
    thread_id=thread.id
  )
  print(messages)
else:
  print(run.status)
```

```javascript
if (run.status === 'completed') {
  const messages = await openai.beta.threads.messages.list(
    run.thread_id
  );
  for (const message of messages.data.reverse()) {
    console.log(`${message.role} > ${message.content[0].text.value}`);
  }
} else {
  console.log(run.status);
}
```

```bash
curl https://api.openai.com/v1/threads/thread_abc123/messages \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "OpenAI-Beta: assistants=v2"
```

You may also want to list the [Run Steps](/docs/api-reference/runs/listRunSteps) of this Run if you'd like to look at any tool calls made during this Run.

Next steps
----------

1.  Continue learning about Assistants Concepts in the [Deep Dive](/docs/assistants/deep-dive)
2.  Learn more about [Tools](/docs/assistants/tools)
3.  Explore the [Assistants playground](/playground?mode=assistant)
4.  Check out our [Assistants Quickstart app](https://github.com/openai/openai-assistants-quickstart) on github


# Assistants API deep dive

================================

In-depth guide to creating and managing assistants.

As described in the [Assistants Overview](/docs/assistants/overview), there are several concepts involved in building an app with the Assistants API.

This guide goes deeper into each of these concepts.

If you want to get started coding right away, check out the [Assistants API Quickstart](/docs/assistants/quickstart).

Creating Assistants
-------------------

We recommend using OpenAI's [latest models](/docs/models#gpt-4-turbo-and-gpt-4) with the Assistants API for best results and maximum compatibility with tools.

To get started, creating an Assistant only requires specifying the `model` to use. But you can further customize the behavior of the Assistant:

1.  Use the `instructions` parameter to guide the personality of the Assistant and define its goals. Instructions are similar to system messages in the Chat Completions API.
2.  Use the `tools` parameter to give the Assistant access to up to 128 tools. You can give it access to OpenAI-hosted tools like `code_interpreter` and `file_search`, or call a third-party tools via a `function` calling.
3.  Use the `tool_resources` parameter to give the tools like `code_interpreter` and `file_search` access to files. Files are uploaded using the `File` [upload endpoint](/docs/api-reference/files/create) and must have the `purpose` set to `assistants` to be used with this API.

For example, to create an Assistant that can create data visualization based on a `.csv` file, first upload a file.

```python
file = client.files.create(
  file=open("revenue-forecast.csv", "rb"),
  purpose='assistants'
)
```

```javascript
const file = await openai.files.create({
  file: fs.createReadStream("revenue-forecast.csv"),
  purpose: "assistants",
});
```

```bash
curl https://api.openai.com/v1/files \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -F purpose="assistants" \
  -F file="@revenue-forecast.csv"
```

Then, create the Assistant with the `code_interpreter` tool enabled and provide the file as a resource to the tool.

```python
assistant = client.beta.assistants.create(
  name="Data visualizer",
  description="You are great at creating beautiful data visualizations. You analyze data present in .csv files, understand trends, and come up with data visualizations relevant to those trends. You also share a brief text summary of the trends observed.",
  model="gpt-4o",
  tools=[{"type": "code_interpreter"}],
  tool_resources={
    "code_interpreter": {
      "file_ids": [file.id]
    }
  }
)
```

```javascript
const assistant = await openai.beta.assistants.create({
  name: "Data visualizer",
  description: "You are great at creating beautiful data visualizations. You analyze data present in .csv files, understand trends, and come up with data visualizations relevant to those trends. You also share a brief text summary of the trends observed.",
  model: "gpt-4o",
  tools: [{"type": "code_interpreter"}],
  tool_resources: {
    "code_interpreter": {
      "file_ids": [file.id]
    }
  }
});
```

```bash
curl https://api.openai.com/v1/assistants \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -H "OpenAI-Beta: assistants=v2" \
  -d '{
    "name": "Data visualizer",
    "description": "You are great at creating beautiful data visualizations. You analyze data present in .csv files, understand trends, and come up with data visualizations relevant to those trends. You also share a brief text summary of the trends observed.",
    "model": "gpt-4o",
    "tools": [{"type": "code_interpreter"}],
    "tool_resources": {
      "code_interpreter": {
        "file_ids": ["file-BK7bzQj3FfZFXr7DbL6xJwfo"]
      }
    }
  }'
```

You can attach a maximum of 20 files to `code_interpreter` and 10,000 files to `file_search` (using `vector_store` [objects](/docs/api-reference/vector-stores/object)).

Each file can be at most 512 MB in size and have a maximum of 5,000,000 tokens. By default, the size of all the files uploaded in your project cannot exceed 100 GB, but you can reach out to our support team to increase this limit.

Managing Threads and Messages
-----------------------------

Threads and Messages represent a conversation session between an Assistant and a user. There is a limit of 100,000 Messages per Thread. Once the size of the Messages exceeds the context window of the model, the Thread will attempt to smartly truncate messages, before fully dropping the ones it considers the least important.

You can create a Thread with an initial list of Messages like this:

```python
thread = client.beta.threads.create(
  messages=[
    {
      "role": "user",
      "content": "Create 3 data visualizations based on the trends in this file.",
      "attachments": [
        {
          "file_id": file.id,
          "tools": [{"type": "code_interpreter"}]
        }
      ]
    }
  ]
)
```

```javascript
const thread = await openai.beta.threads.create({
  messages: [
    {
      "role": "user",
      "content": "Create 3 data visualizations based on the trends in this file.",
      "attachments": [
        {
          file_id: file.id,
          tools: [{type: "code_interpreter"}]
        }
      ]
    }
  ]
});
```

```bash
curl https://api.openai.com/v1/threads \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -H "OpenAI-Beta: assistants=v2" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "Create 3 data visualizations based on the trends in this file.",
        "attachments": [
          {
            "file_id": "file-ACq8OjcLQm2eIG0BvRM4z5qX",
            "tools": [{"type": "code_interpreter"}]
          }
        ]
      }
    ]
  }'
```

Messages can contain text, images, or file attachment. Message `attachments` are helper methods that add files to a thread's `tool_resources`. You can also choose to add files to the `thread.tool_resources` directly.

### Creating image input content

Message content can contain either external image URLs or File IDs uploaded via the [File API](/docs/api-reference/files/create). Only [models](/docs/models) with Vision support can accept image input. Supported image content types include png, jpg, gif, and webp. When creating image files, pass `purpose="vision"` to allow you to later download and display the input content. Currently, there is a 100GB limit per project. Please contact us to request a limit increase.

Tools cannot access image content unless specified. To pass image files to Code Interpreter, add the file ID in the message `attachments` list to allow the tool to read and analyze the input. Image URLs cannot be downloaded in Code Interpreter today.

```python
file = client.files.create(
  file=open("myimage.png", "rb"),
  purpose="vision"
)
thread = client.beta.threads.create(
  messages=[
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "What is the difference between these images?"
        },
        {
          "type": "image_url",
          "image_url": {"url": "https://example.com/image.png"}
        },
        {
          "type": "image_file",
          "image_file": {"file_id": file.id}
        },
      ],
    }
  ]
)
```

```javascript
import fs from "fs";
const file = await openai.files.create({
  file: fs.createReadStream("myimage.png"),
  purpose: "vision",
});
const thread = await openai.beta.threads.create({
  messages: [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "What is the difference between these images?"
        },
        {
          "type": "image_url",
          "image_url": {"url": "https://example.com/image.png"}
        },
        {
          "type": "image_file",
          "image_file": {"file_id": file.id}
        },
      ]
    }
  ]
});
```

```bash
# Upload a file with an "vision" purpose
curl https://api.openai.com/v1/files \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -F purpose="vision" \
  -F file="@/path/to/myimage.png"

## Pass the file ID in the content
curl https://api.openai.com/v1/threads \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -H "OpenAI-Beta: assistants=v2" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": [
          {
            "type": "text",
            "text": "What is the difference between these images?"
          },
          {
            "type": "image_url",
            "image_url": {"url": "https://example.com/image.png"}
          },
          {
            "type": "image_file",
            "image_file": {"file_id": file.id}
          }
        ]
      }
    ]
  }'
```

#### Low or high fidelity image understanding

By controlling the `detail` parameter, which has three options, `low`, `high`, or `auto`, you have control over how the model processes the image and generates its textual understanding.

*   `low` will enable the "low res" mode. The model will receive a low-res 512px x 512px version of the image, and represent the image with a budget of 85 tokens. This allows the API to return faster responses and consume fewer input tokens for use cases that do not require high detail.
*   `high` will enable "high res" mode, which first allows the model to see the low res image and then creates detailed crops of input images based on the input image size. Use the [pricing calculator](https://openai.com/api/pricing/) to see token counts for various image sizes.

```python
thread = client.beta.threads.create(
  messages=[
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "What is this an image of?"
        },
        {
          "type": "image_url",
          "image_url": {
            "url": "https://example.com/image.png",
            "detail": "high"
          }
        },
      ],
    }
  ]
)
```

```javascript
const thread = await openai.beta.threads.create({
  messages: [
    {
      "role": "user",
      "content": [
          {
            "type": "text",
            "text": "What is this an image of?"
          },
          {
            "type": "image_url",
            "image_url": {
              "url": "https://example.com/image.png",
              "detail": "high"
            }
          },
      ]
    }
  ]
});
```

```bash
curl https://api.openai.com/v1/threads \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -H "OpenAI-Beta: assistants=v2" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": [
          {
            "type": "text",
            "text": "What is this an image of?"
          },
          {
            "type": "image_url",
            "image_url": {
              "url": "https://example.com/image.png",
              "detail": "high"
            }
          },
        ]
      }
    ]
  }'
```

### Context window management

The Assistants API automatically manages the truncation to ensure it stays within the model's maximum context length. You can customize this behavior by specifying the maximum tokens you'd like a run to utilize and/or the maximum number of recent messages you'd like to include in a run.

#### Max Completion and Max Prompt Tokens

To control the token usage in a single Run, set `max_prompt_tokens` and `max_completion_tokens` when creating the Run. These limits apply to the total number of tokens used in all completions throughout the Run's lifecycle.

For example, initiating a Run with `max_prompt_tokens` set to 500 and `max_completion_tokens` set to 1000 means the first completion will truncate the thread to 500 tokens and cap the output at 1000 tokens. If only 200 prompt tokens and 300 completion tokens are used in the first completion, the second completion will have available limits of 300 prompt tokens and 700 completion tokens.

If a completion reaches the `max_completion_tokens` limit, the Run will terminate with a status of `incomplete`, and details will be provided in the `incomplete_details` field of the Run object.

When using the File Search tool, we recommend setting the max\_prompt\_tokens to no less than 20,000. For longer conversations or multiple interactions with File Search, consider increasing this limit to 50,000, or ideally, removing the max\_prompt\_tokens limits altogether to get the highest quality results.

#### Truncation Strategy

You may also specify a truncation strategy to control how your thread should be rendered into the model's context window. Using a truncation strategy of type `auto` will use OpenAI's default truncation strategy. Using a truncation strategy of type `last_messages` will allow you to specify the number of the most recent messages to include in the context window.

### Message annotations

Messages created by Assistants may contain [`annotations`](/docs/api-reference/messages/object#messages/object-content) within the `content` array of the object. Annotations provide information around how you should annotate the text in the Message.

There are two types of Annotations:

1.  `file_citation`: File citations are created by the [`file_search`](/docs/assistants/tools/file-search) tool and define references to a specific file that was uploaded and used by the Assistant to generate the response.
2.  `file_path`: File path annotations are created by the [`code_interpreter`](/docs/assistants/tools/code-interpreter) tool and contain references to the files generated by the tool.

When annotations are present in the Message object, you'll see illegible model-generated substrings in the text that you should replace with the annotations. These strings may look something like `【13†source】` or `sandbox:/mnt/data/file.csv`. Here’s an example python code snippet that replaces these strings with the annotations.

```python
# Retrieve the message object
message = client.beta.threads.messages.retrieve(
  thread_id="...",
  message_id="..."
)

# Extract the message content
message_content = message.content[0].text
annotations = message_content.annotations
citations = []

# Iterate over the annotations and add footnotes
for index, annotation in enumerate(annotations):
    # Replace the text with a footnote
    message_content.value = message_content.value.replace(annotation.text, f' [{index}]')
    
    # Gather citations based on annotation attributes
    if (file_citation := getattr(annotation, 'file_citation', None)):
        cited_file = client.files.retrieve(file_citation.file_id)
        citations.append(f'[{index}] {file_citation.quote} from {cited_file.filename}')
    elif (file_path := getattr(annotation, 'file_path', None)):
        cited_file = client.files.retrieve(file_path.file_id)
        citations.append(f'[{index}] Click <here> to download {cited_file.filename}')
        # Note: File download functionality not implemented above for brevity

# Add footnotes to the end of the message before displaying to user
message_content.value += '\n' + '\n'.join(citations)
```

Runs and Run Steps
------------------

When you have all the context you need from your user in the Thread, you can run the Thread with an Assistant of your choice.

```python
run = client.beta.threads.runs.create(
  thread_id=thread.id,
  assistant_id=assistant.id
)
```

```javascript
const run = await openai.beta.threads.runs.create(
  thread.id,
  { assistant_id: assistant.id }
);
```

```bash
curl https://api.openai.com/v1/threads/THREAD_ID/runs \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -H "OpenAI-Beta: assistants=v2" \
  -d '{
    "assistant_id": "asst_ToSF7Gb04YMj8AMMm50ZLLtY"
  }'
```

By default, a Run will use the `model` and `tools` configuration specified in Assistant object, but you can override most of these when creating the Run for added flexibility:

```python
run = client.beta.threads.runs.create(
  thread_id=thread.id,
  assistant_id=assistant.id,
  model="gpt-4o",
  instructions="New instructions that override the Assistant instructions",
  tools=[{"type": "code_interpreter"}, {"type": "file_search"}]
)
```

```javascript
const run = await openai.beta.threads.runs.create(
  thread.id,
  {
    assistant_id: assistant.id,
    model: "gpt-4o",
    instructions: "New instructions that override the Assistant instructions",
    tools: [{"type": "code_interpreter"}, {"type": "file_search"}]
  }
);
```

```bash
curl https://api.openai.com/v1/threads/THREAD_ID/runs \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -H "OpenAI-Beta: assistants=v2" \
  -d '{
    "assistant_id": "ASSISTANT_ID",
    "model": "gpt-4o",
    "instructions": "New instructions that override the Assistant instructions",
    "tools": [{"type": "code_interpreter"}, {"type": "file_search"}]
  }'
```

Note: `tool_resources` associated with the Assistant cannot be overridden during Run creation. You must use the [modify Assistant](/docs/api-reference/assistants/modifyAssistant) endpoint to do this.

#### Run lifecycle

Run objects can have multiple statuses.

![Run lifecycle - diagram showing possible status transitions](https://cdn.openai.com/API/docs/images/diagram-run-statuses-v2.png)

|Status|Definition|
|---|---|
|queued|When Runs are first created or when you complete the required_action, they are moved to a queued status. They should almost immediately move to in_progress.|
|in_progress|While in_progress, the Assistant uses the model and tools to perform steps. You can view progress being made by the Run by examining the Run Steps.|
|completed|The Run successfully completed! You can now view all Messages the Assistant added to the Thread, and all the steps the Run took. You can also continue the conversation by adding more user Messages to the Thread and creating another Run.|
|requires_action|When using the Function calling tool, the Run will move to a required_action state once the model determines the names and arguments of the functions to be called. You must then run those functions and submit the outputs before the run proceeds. If the outputs are not provided before the expires_at timestamp passes (roughly 10 mins past creation), the run will move to an expired status.|
|expired|This happens when the function calling outputs were not submitted before expires_at and the run expires. Additionally, if the runs take too long to execute and go beyond the time stated in expires_at, our systems will expire the run.|
|cancelling|You can attempt to cancel an in_progress run using the Cancel Run endpoint. Once the attempt to cancel succeeds, status of the Run moves to cancelled. Cancellation is attempted but not guaranteed.|
|cancelled|Run was successfully cancelled.|
|failed|You can view the reason for the failure by looking at the last_error object in the Run. The timestamp for the failure will be recorded under failed_at.|
|incomplete|Run ended due to max_prompt_tokens or max_completion_tokens reached. You can view the specific reason by looking at the incomplete_details object in the Run.|

#### Polling for updates

If you are not using [streaming](/docs/assistants/overview#step-4-create-a-run?context=with-streaming), in order to keep the status of your run up to date, you will have to periodically [retrieve the Run](/docs/api-reference/runs/getRun) object. You can check the status of the run each time you retrieve the object to determine what your application should do next.

You can optionally use Polling Helpers in our [Node](https://github.com/openai/openai-node?tab=readme-ov-file#polling-helpers) and [Python](https://github.com/openai/openai-python?tab=readme-ov-file#polling-helpers) SDKs to help you with this. These helpers will automatically poll the Run object for you and return the Run object when it's in a terminal state.

#### Thread locks

When a Run is `in_progress` and not in a terminal state, the Thread is locked. This means that:

*   New Messages cannot be added to the Thread.
*   New Runs cannot be created on the Thread.

#### Run steps

![Run steps lifecycle - diagram showing possible status transitions](https://cdn.openai.com/API/docs/images/diagram-2.png)

Run step statuses have the same meaning as Run statuses.

Most of the interesting detail in the Run Step object lives in the `step_details` field. There can be two types of step details:

1.  `message_creation`: This Run Step is created when the Assistant creates a Message on the Thread.
2.  `tool_calls`: This Run Step is created when the Assistant calls a tool. Details around this are covered in the relevant sections of the [Tools](/docs/assistants/tools) guide.

Data Access Guidance
--------------------

Currently, Assistants, Threads, Messages, and Vector Stores created via the API are scoped to the Project they're created in. As such, any person with API key access to that Project is able to read or write Assistants, Threads, Messages, and Runs in the Project.

We strongly recommend the following data access controls:

*   _Implement authorization._ Before performing reads or writes on Assistants, Threads, Messages, and Vector Stores, ensure that the end-user is authorized to do so. For example, store in your database the object IDs that the end-user has access to, and check it before fetching the object ID with the API.
*   _Restrict API key access._ Carefully consider who in your organization should have API keys and be part of a Project. Periodically audit this list. API keys enable a wide range of operations including reading and modifying sensitive information, such as Messages and Files.
*   _Create separate accounts._ Consider creating separate Projects for different applications in order to isolate data across multiple applications.

# Assistants API tools

============================

Explore tools for file search, code, and function calling.

Assistants created using the Assistants API can be equipped with tools that allow them to perform more complex tasks or interact with your application. We provide built-in tools for assistants, but you can also define your own tools to extend their capabilities using Function Calling.

## Assistants File Search

==============================

File Search augments the Assistant with knowledge from outside its model, such as proprietary product information or documents provided by your users. OpenAI automatically parses and chunks your documents, creates and stores the embeddings, and use both vector and keyword search to retrieve relevant content to answer user queries.

Quickstart
----------

In this example, we’ll create an assistant that can help answer questions about companies’ financial statements.

### Step 1: Create a new Assistant with File Search Enabled

Create a new assistant with `file_search` enabled in the `tools` parameter of the Assistant.

```python
from openai import OpenAI

client = OpenAI()

assistant = client.beta.assistants.create(
  name="Financial Analyst Assistant",
  instructions="You are an expert financial analyst. Use you knowledge base to answer questions about audited financial statements.",
  model="gpt-4o",
  tools=[{"type": "file_search"}],
)
```

```javascript
import OpenAI from "openai";
const openai = new OpenAI();

async function main() {
  const assistant = await openai.beta.assistants.create({
    name: "Financial Analyst Assistant",
    instructions: "You are an expert financial analyst. Use you knowledge base to answer questions about audited financial statements.",
    model: "gpt-4o",
    tools: [{ type: "file_search" }],
  });
}

main();
```

```bash
curl https://api.openai.com/v1/assistants \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "OpenAI-Beta: assistants=v2" \
  -d '{
    "name": "Financial Analyst Assistant",
    "instructions": "You are an expert financial analyst. Use you knowledge base to answer questions about audited financial statements.",
    "tools": [{"type": "file_search"}],
    "model": "gpt-4o"
  }'
```

Once the `file_search` tool is enabled, the model decides when to retrieve content based on user messages.

### Step 2: Upload files and add them to a Vector Store

To access your files, the `file_search` tool uses the Vector Store object.  
Upload your files and create a Vector Store to contain them.  
Once the Vector Store is created, you should poll its status until all files are out of the `in_progress` state to  
ensure that all content has finished processing. The SDK provides helpers to uploading and polling in one shot.

```python
# Create a vector store caled "Financial Statements"
vector_store = client.beta.vector_stores.create(name="Financial Statements")

# Ready the files for upload to OpenAI
file_paths = ["edgar/goog-10k.pdf", "edgar/brka-10k.txt"]
file_streams = [open(path, "rb") for path in file_paths]

# Use the upload and poll SDK helper to upload the files, add them to the vector store,
# and poll the status of the file batch for completion.
file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
  vector_store_id=vector_store.id, files=file_streams
)

# You can print the status and the file counts of the batch to see the result of this operation.
print(file_batch.status)
print(file_batch.file_counts)
```

```javascript
const fileStreams = ["edgar/goog-10k.pdf", "edgar/brka-10k.txt"].map((path) =>
  fs.createReadStream(path),
);

// Create a vector store including our two files.
let vectorStore = await openai.beta.vectorStores.create({
  name: "Financial Statement",
});

await openai.beta.vectorStores.fileBatches.uploadAndPoll(vectorStore.id, fileStreams)
```

### Step 3: Update the assistant to use the new Vector Store

To make the files accessible to your assistant, update the assistant’s `tool_resources` with the new `vector_store` id.

```python
assistant = client.beta.assistants.update(
  assistant_id=assistant.id,
  tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
)
```

```javascript
await openai.beta.assistants.update(assistant.id, {
  tool_resources: { file_search: { vector_store_ids: [vectorStore.id] } },
});
```

### Step 4: Create a thread

You can also attach files as Message attachments on your thread. Doing so will create another `vector_store` associated with the thread, or, if there is already a vector store attached to this thread, attach the new files to the existing thread vector store. When you create a Run on this thread, the file search tool will query both the `vector_store` from your assistant and the `vector_store` on the thread.

In this example, the user attached a copy of Apple’s latest 10-K filing.

```python
# Upload the user provided file to OpenAI
message_file = client.files.create(
  file=open("edgar/aapl-10k.pdf", "rb"), purpose="assistants"
)

# Create a thread and attach the file to the message
thread = client.beta.threads.create(
  messages=[
    {
      "role": "user",
      "content": "How many shares of AAPL were outstanding at the end of of October 2023?",
      # Attach the new file to the message.
      "attachments": [
        { "file_id": message_file.id, "tools": [{"type": "file_search"}] }
      ],
    }
  ]
)

# The thread now has a vector store with that file in its tool resources.
print(thread.tool_resources.file_search)
```

```javascript
// A user wants to attach a file to a specific message, let's upload it.
const aapl10k = await openai.files.create({
  file: fs.createReadStream("edgar/aapl-10k.pdf"),
  purpose: "assistants",
});

const thread = await openai.beta.threads.create({
  messages: [
    {
      role: "user",
      content:
        "How many shares of AAPL were outstanding at the end of of October 2023?",
      // Attach the new file to the message.
      attachments: [{ file_id: aapl10k.id, tools: [{ type: "file_search" }] }],
    },
  ],
});

// The thread now has a vector store in its tool resources.
console.log(thread.tool_resources?.file_search);
```

Vector stores created using message attachments have a default expiration policy of 7 days after they were last active (defined as the last time the vector store was part of a run). This default exists to help you manage your vector storage costs. You can override these expiration policies at any time. Learn more [here](#managing-costs-with-expiration-policies).

### Step 5: Create a run and check the output

Now, create a Run and observe that the model uses the File Search tool to provide a response to the user’s question.

With streaming

```python
from typing_extensions import override
from openai import AssistantEventHandler, OpenAI

client = OpenAI()

class EventHandler(AssistantEventHandler):
    @override
    def on_text_created(self, text) -> None:
        print(f"\nassistant > ", end="", flush=True)

    @override
    def on_tool_call_created(self, tool_call):
        print(f"\nassistant > {tool_call.type}\n", flush=True)

    @override
    def on_message_done(self, message) -> None:
        # print a citation to the file searched
        message_content = message.content[0].text
        annotations = message_content.annotations
        citations = []
        for index, annotation in enumerate(annotations):
            message_content.value = message_content.value.replace(
                annotation.text, f"[{index}]"
            )
            if file_citation := getattr(annotation, "file_citation", None):
                cited_file = client.files.retrieve(file_citation.file_id)
                citations.append(f"[{index}] {cited_file.filename}")

        print(message_content.value)
        print("\n".join(citations))

# Then, we use the stream SDK helper
# with the EventHandler class to create the Run
# and stream the response.

with client.beta.threads.runs.stream(
    thread_id=thread.id,
    assistant_id=assistant.id,
    instructions="Please address the user as Jane Doe. The user has a premium account.",
    event_handler=EventHandler(),
) as stream:
    stream.until_done()
```

```javascript
const stream = openai.beta.threads.runs
  .stream(thread.id, {
    assistant_id: assistant.id,
  })
  .on("textCreated", () => console.log("assistant >"))
  .on("toolCallCreated", (event) => console.log("assistant " + event.type))
  .on("messageDone", async (event) => {
    if (event.content[0].type === "text") {
      const { text } = event.content[0];
      const { annotations } = text;
      const citations: string[] = [];

      let index = 0;
      for (let annotation of annotations) {
        text.value = text.value.replace(annotation.text, "[" + index + "]");
        const { file_citation } = annotation;
        if (file_citation) {
          const citedFile = await openai.files.retrieve(file_citation.file_id);
          citations.push("[" + index + "]" + citedFile.filename);
        }
        index++;
      }

      console.log(text.value);
      console.log(citations.join("\n"));
    }
```

Without streaming

```python
# Use the create and poll SDK helper to create a run and poll the status of
# the run until it's in a terminal state.

run = client.beta.threads.runs.create_and_poll(
    thread_id=thread.id, assistant_id=assistant.id
)

messages = list(client.beta.threads.messages.list(thread_id=thread.id, run_id=run.id))

message_content = messages[0].content[0].text
annotations = message_content.annotations
citations = []
for index, annotation in enumerate(annotations):
    message_content.value = message_content.value.replace(annotation.text, f"[{index}]")
    if file_citation := getattr(annotation, "file_citation", None):
        cited_file = client.files.retrieve(file_citation.file_id)
        citations.append(f"[{index}] {cited_file.filename}")

print(message_content.value)
print("\n".join(citations))
```

```javascript
const run = await openai.beta.threads.runs.createAndPoll(thread.id, {
  assistant_id: assistant.id,
});

const messages = await openai.beta.threads.messages.list(thread.id, {
  run_id: run.id,
});

const message = messages.data.pop()!;
if (message.content[0].type === "text") {
  const { text } = message.content[0];
  const { annotations } = text;
  const citations: string[] = [];

  let index = 0;
  for (let annotation of annotations) {
    text.value = text.value.replace(annotation.text, "[" + index + "]");
    const { file_citation } = annotation;
    if (file_citation) {
      const citedFile = await openai.files.retrieve(file_citation.file_id);
      citations.push("[" + index + "]" + citedFile.filename);
    }
    index++;
  }

  console.log(text.value);
  console.log(citations.join("\n"));
}
```

Your new assistant will query both attached vector stores (one containing `goog-10k.pdf` and `brka-10k.txt`, and the other containing `aapl-10k.pdf`) and return this result from `aapl-10k.pdf`.

To retrieve the contents of the file search results that were used by the model, use the `include` query parameter and provide a value of `step_details.tool_calls[*].file_search.results[*].content` in the format `?include[]=step_details.tool_calls[*].file_search.results[*].content`.

* * *

How it works
------------

The `file_search` tool implements several retrieval best practices out of the box to help you extract the right data from your files and augment the model’s responses. The `file_search` tool:

*   Rewrites user queries to optimize them for search.
*   Breaks down complex user queries into multiple searches it can run in parallel.
*   Runs both keyword and semantic searches across both assistant and thread vector stores.
*   Reranks search results to pick the most relevant ones before generating the final response.

By default, the `file_search` tool uses the following settings but these can be [configured](#customizing-file-search-settings) to suit your needs:

*   Chunk size: 800 tokens
*   Chunk overlap: 400 tokens
*   Embedding model: `text-embedding-3-large` at 256 dimensions
*   Maximum number of chunks added to context: 20 (could be fewer)
*   Ranker: `auto` (OpenAI will choose which ranker to use)
*   Score threshold: 0 minimum ranking score

**Known Limitations**

We have a few known limitations we're working on adding support for in the coming months:

1.  Support for deterministic pre-search filtering using custom metadata.
2.  Support for parsing images within documents (including images of charts, graphs, tables etc.)
3.  Support for retrievals over structured file formats (like `csv` or `jsonl`).
4.  Better support for summarization — the tool today is optimized for search queries.

Vector stores
-------------

Vector Store objects give the File Search tool the ability to search your files. Adding a file to a `vector_store` automatically parses, chunks, embeds and stores the file in a vector database that's capable of both keyword and semantic search. Each `vector_store` can hold up to 10,000 files. Vector stores can be attached to both Assistants and Threads. Today, you can attach at most one vector store to an assistant and at most one vector store to a thread.

#### Creating vector stores and adding files

You can create a vector store and add files to it in a single API call:

```python
vector_store = client.beta.vector_stores.create(
  name="Product Documentation",
  file_ids=['file_1', 'file_2', 'file_3', 'file_4', 'file_5']
)
```

```javascript
const vectorStore = await openai.beta.vectorStores.create({
  name: "Product Documentation",
  file_ids: ['file_1', 'file_2', 'file_3', 'file_4', 'file_5']
});
```

Adding files to vector stores is an async operation. To ensure the operation is complete, we recommend that you use the 'create and poll' helpers in our official SDKs. If you're not using the SDKs, you can retrieve the `vector_store` object and monitor its [`file_counts`](/docs/api-reference/vector-stores/object#vector-stores/object-file_counts) property to see the result of the file ingestion operation.

Files can also be added to a vector store after it's created by [creating vector store files](/docs/api-reference/vector-stores/createFile).

```python
file = client.beta.vector_stores.files.create_and_poll(
  vector_store_id="vs_abc123",
  file_id="file-abc123"
)
```

```javascript
const file = await openai.beta.vectorStores.files.createAndPoll(
  "vs_abc123",
  { file_id: "file-abc123" }
);
```

Alternatively, you can add several files to a vector store by [creating batches](/docs/api-reference/vector-stores/createBatch) of up to 500 files.

```python
batch = client.beta.vector_stores.file_batches.create_and_poll(
  vector_store_id="vs_abc123",
  file_ids=['file_1', 'file_2', 'file_3', 'file_4', 'file_5']
)
```

```javascript
const batch = await openai.beta.vectorStores.fileBatches.createAndPoll(
  "vs_abc123",
  { file_ids: ["file_1", "file_2", "file_3", "file_4", "file_5"] },
);
```

Similarly, these files can be removed from a vector store by either:

*   Deleting the [vector store file object](/docs/api-reference/vector-stores/deleteFile) or,
*   By deleting the underlying [file object](/docs/api-reference/files/delete) (which removes the file it from all `vector_store` and `code_interpreter` configurations across all assistants and threads in your organization)

The maximum file size is 512 MB. Each file should contain no more than 5,000,000 tokens per file (computed automatically when you attach a file).

File Search supports a variety of file formats including `.pdf`, `.md`, and `.docx`. More details on the file extensions (and their corresponding MIME-types) supported can be found in the [Supported files](#supported-files) section below.

#### Attaching vector stores

You can attach vector stores to your Assistant or Thread using the `tool_resources` parameter.

```python
assistant = client.beta.assistants.create(
  instructions="You are a helpful product support assistant and you answer questions based on the files provided to you.",
  model="gpt-4o",
  tools=[{"type": "file_search"}],
  tool_resources={
    "file_search": {
      "vector_store_ids": ["vs_1"]
    }
  }
)

thread = client.beta.threads.create(
  messages=[ { "role": "user", "content": "How do I cancel my subscription?"} ],
  tool_resources={
    "file_search": {
      "vector_store_ids": ["vs_2"]
    }
  }
)
```

```javascript
const assistant = await openai.beta.assistants.create({
  instructions: "You are a helpful product support assistant and you answer questions based on the files provided to you.",
  model: "gpt-4o",
  tools: [{"type": "file_search"}],
  tool_resources: {
    "file_search": {
      "vector_store_ids": ["vs_1"]
    }
  }
});

const thread = await openai.beta.threads.create({
  messages: [ { role: "user", content: "How do I cancel my subscription?"} ],
  tool_resources: {
    "file_search": {
      "vector_store_ids": ["vs_2"]
    }
  }
});
```

You can also attach a vector store to Threads or Assistants after they're created by updating them with the right `tool_resources`.

#### Ensuring vector store readiness before creating runs

We highly recommend that you ensure all files in a `vector_store` are fully processed before you create a run. This will ensure that all the data in your `vector_store` is searchable. You can check for `vector_store` readiness by using the polling helpers in our SDKs, or by manually polling the `vector_store` object to ensure the [`status`](/docs/api-reference/vector-stores/object#vector-stores/object-status) is `completed`.

As a fallback, we've built a **60 second maximum wait** in the Run object when the **thread’s** vector store contains files that are still being processed. This is to ensure that any files your users upload in a thread a fully searchable before the run proceeds. This fallback wait _does not_ apply to the assistant's vector store.

#### Customizing File Search settings

You can customize how the `file_search` tool chunks your data and how many chunks it returns to the model context.

**Chunking configuration**

By default, `max_chunk_size_tokens` is set to `800` and `chunk_overlap_tokens` is set to `400`, meaning every file is indexed by being split up into 800-token chunks, with 400-token overlap between consecutive chunks.

You can adjust this by setting [`chunking_strategy`](/docs/api-reference/vector-stores-files/createFile#vector-stores-files-createfile-chunking_strategy) when adding files to the vector store. There are certain limitations to `chunking_strategy`:

*   `max_chunk_size_tokens` must be between 100 and 4096 inclusive.
*   `chunk_overlap_tokens` must be non-negative and should not exceed `max_chunk_size_tokens / 2`.

**Number of chunks**

By default, the `file_search` tool outputs up to 20 chunks for `gpt-4*` models and up to 5 chunks for `gpt-3.5-turbo`. You can adjust this by setting [`file_search.max_num_results`](/docs/api-reference/assistants/createAssistant#assistants-createassistant-tools) in the tool when creating the assistant or the run.

Note that the `file_search` tool may output fewer than this number for a myriad of reasons:

*   The total number of chunks is fewer than `max_num_results`.
*   The total token size of all the retrieved chunks exceeds the token "budget" assigned to the `file_search` tool. The `file_search` tool currently has a token bugdet of:
    *   4,000 tokens for `gpt-3.5-turbo`
    *   16,000 tokens for `gpt-4*` models

#### Improve file search result relevance with chunk ranking

By default, the file search tool will return all search results to the model that it thinks have any level of relevance when generating a response. However, if responses are generated using content that has low relevance, it can lead to lower quality responses. You can adjust this behavior by both inspecting the file search results that are returned when generating responses, and then tuning the behavior of the file search tool's ranker to change how relevant results must be before they are used to generate a response.

**Inspecting file search chunks**

The first step in improving the quality of your file search results is inspecting the current behavior of your assistant. Most often, this will involve investigating responses from your assistant that are not not performing well. You can get [granular information about a past run step](/docs/api-reference/run-steps/getRunStep) using the REST API, specifically using the `include` query parameter to get the file chunks that are being used to generate results.

Include file search results in response when creating a run

```python
from openai import OpenAI
client = OpenAI()

run_step = client.beta.threads.runs.steps.retrieve(
    thread_id="thread_abc123",
    run_id="run_abc123",
    step_id="step_abc123",
    include=["step_details.tool_calls[*].file_search.results[*].content"]
)

print(run_step)
```

```javascript
import OpenAI from "openai";
const openai = new OpenAI();

const runStep = await openai.beta.threads.runs.steps.retrieve(
  "thread_abc123",
  "run_abc123",
  "step_abc123",
  {
    include: ["step_details.tool_calls[*].file_search.results[*].content"]
  }
);

console.log(runStep);
```

```bash
curl -g https://api.openai.com/v1/threads/thread_abc123/runs/run_abc123/steps/step_abc123?include[]=step_details.tool_calls[*].file_search.results[*].content \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -H "OpenAI-Beta: assistants=v2"
```

You can then log and inspect the search results used during the run step, and determine whether or not they are consistently relevant to the responses your assistant should generate.

**Configure ranking options**

If you have determined that your file search results are not sufficiently relevant to generate high quality responses, you can adjust the settings of the result ranker used to choose which search results should be used to generate responses. You can adjust this setting [`file_search.ranking_options`](/docs/api-reference/assistants/createAssistant#assistants-createassistant-tools) in the tool when **creating the assistant** or **creating the run**.

The settings you can configure are:

*   `ranker` - Which ranker to use in determining which chunks to use. The available values are `auto`, which uses the latest available ranker, and `default_2024_08_21`.
*   `score_threshold` - a ranking between 0.0 and 1.0, with 1.0 being the highest ranking. A higher number will constrain the file chunks used to generate a result to only chunks with a higher possible relevance, at the cost of potentially leaving out relevant chunks.

#### Managing costs with expiration policies

The `file_search` tool uses the `vector_stores` object as its resource and you will be billed based on the [size](/docs/api-reference/vector-stores/object#vector-stores/object-bytes) of the `vector_store` objects created. The size of the vector store object is the sum of all the parsed chunks from your files and their corresponding embeddings.

You first GB is free and beyond that, usage is billed at $0.10/GB/day of vector storage. There are no other costs associated with vector store operations.

In order to help you manage the costs associated with these `vector_store` objects, we have added support for expiration policies in the `vector_store` object. You can set these policies when creating or updating the `vector_store` object.

```python
vector_store = client.beta.vector_stores.create_and_poll(
  name="Product Documentation",
  file_ids=['file_1', 'file_2', 'file_3', 'file_4', 'file_5'],
  expires_after={
    "anchor": "last_active_at",
    "days": 7
  }
)
```

```javascript
let vectorStore = await openai.beta.vectorStores.create({
  name: "rag-store",
  file_ids: ['file_1', 'file_2', 'file_3', 'file_4', 'file_5'],
  expires_after: {
    anchor: "last_active_at",
    days: 7
  }
});
```

**Thread vector stores have default expiration policies**

Vector stores created using thread helpers (like [`tool_resources.file_search.vector_stores`](/docs/api-reference/threads/createThread#threads-createthread-tool_resources) in Threads or [message.attachments](/docs/api-reference/messages/createMessage#messages-createmessage-attachments) in Messages) have a default expiration policy of 7 days after they were last active (defined as the last time the vector store was part of a run).

When a vector store expires, runs on that thread will fail. To fix this, you can simply recreate a new `vector_store` with the same files and reattach it to the thread.

```python
all_files = list(client.beta.vector_stores.files.list("vs_expired"))

vector_store = client.beta.vector_stores.create(name="rag-store")
client.beta.threads.update(
    "thread_abc123",
    tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
)

for file_batch in chunked(all_files, 100):
    client.beta.vector_stores.file_batches.create_and_poll(
        vector_store_id=vector_store.id, file_ids=[file.id for file in file_batch]
    )
```

```javascript
const fileIds = [];
for await (const file of openai.beta.vectorStores.files.list(
  "vs_toWTk90YblRLCkbE2xSVoJlF",
)) {
  fileIds.push(file.id);
}

const vectorStore = await openai.beta.vectorStores.create({
  name: "rag-store",
});
await openai.beta.threads.update("thread_abcd", {
  tool_resources: { file_search: { vector_store_ids: [vectorStore.id] } },
});

for (const fileBatch of _.chunk(fileIds, 100)) {
  await openai.beta.vectorStores.fileBatches.create(vectorStore.id, {
    file_ids: fileBatch,
  });
}
```

Supported files
---------------

_For `text/` MIME types, the encoding must be one of `utf-8`, `utf-16`, or `ascii`._

|File format|MIME type|
|---|---|
|.c|text/x-c|
|.cpp|text/x-c++|
|.cs|text/x-csharp|
|.css|text/css|
|.doc|application/msword|
|.docx|application/vnd.openxmlformats-officedocument.wordprocessingml.document|
|.go|text/x-golang|
|.html|text/html|
|.java|text/x-java|
|.js|text/javascript|
|.json|application/json|
|.md|text/markdown|
|.pdf|application/pdf|
|.php|text/x-php|
|.pptx|application/vnd.openxmlformats-officedocument.presentationml.presentation|
|.py|text/x-python|
|.py|text/x-script.python|
|.rb|text/x-ruby|
|.sh|application/x-sh|
|.tex|text/x-tex|
|.ts|application/typescript|
|.txt|text/plain|

## Assistants Code Interpreter

===================================

Code Interpreter allows Assistants to write and run Python code in a sandboxed execution environment. This tool can process files with diverse data and formatting, and generate files with data and images of graphs. Code Interpreter allows your Assistant to run code iteratively to solve challenging code and math problems. When your Assistant writes code that fails to run, it can iterate on this code by attempting to run different code until the code execution succeeds.

See a quickstart of how to get started with Code Interpreter [here](/docs/assistants/overview#step-1-create-an-assistant?context=with-streaming).

How it works
------------

Code Interpreter is charged at $0.03 per session. If your Assistant calls Code Interpreter simultaneously in two different threads (e.g., one thread per end-user), two Code Interpreter sessions are created. Each session is active by default for one hour, which means that you only pay for one session per if users interact with Code Interpreter in the same thread for up to one hour.

### Enabling Code Interpreter

Pass `code_interpreter` in the `tools` parameter of the Assistant object to enable Code Interpreter:

```python
assistant = client.beta.assistants.create(
  instructions="You are a personal math tutor. When asked a math question, write and run code to answer the question.",
  model="gpt-4o",
  tools=[{"type": "code_interpreter"}]
)
```

```javascript
const assistant = await openai.beta.assistants.create({
  instructions: "You are a personal math tutor. When asked a math question, write and run code to answer the question.",
  model: "gpt-4o",
  tools: [{"type": "code_interpreter"}]
});
```

```bash
curl https://api.openai.com/v1/assistants \
  -u :$OPENAI_API_KEY \
  -H 'Content-Type: application/json' \
  -H 'OpenAI-Beta: assistants=v2' \
  -d '{
    "instructions": "You are a personal math tutor. When asked a math question, write and run code to answer the question.",
    "tools": [
      { "type": "code_interpreter" }
    ],
    "model": "gpt-4o"
  }'
```

The model then decides when to invoke Code Interpreter in a Run based on the nature of the user request. This behavior can be promoted by prompting in the Assistant's `instructions` (e.g., “write code to solve this problem”).

### Passing files to Code Interpreter

Files that are passed at the Assistant level are accessible by all Runs with this Assistant:

```python
# Upload a file with an "assistants" purpose
file = client.files.create(
  file=open("mydata.csv", "rb"),
  purpose='assistants'
)

# Create an assistant using the file ID
assistant = client.beta.assistants.create(
  instructions="You are a personal math tutor. When asked a math question, write and run code to answer the question.",
  model="gpt-4o",
  tools=[{"type": "code_interpreter"}],
  tool_resources={
    "code_interpreter": {
      "file_ids": [file.id]
    }
  }
)
```

```javascript
// Upload a file with an "assistants" purpose
const file = await openai.files.create({
  file: fs.createReadStream("mydata.csv"),
  purpose: "assistants",
});

// Create an assistant using the file ID
const assistant = await openai.beta.assistants.create({
  instructions: "You are a personal math tutor. When asked a math question, write and run code to answer the question.",
  model: "gpt-4o",
  tools: [{"type": "code_interpreter"}],
  tool_resources: {
    "code_interpreter": {
      "file_ids": [file.id]
    }
  }
});
```

```bash
# Upload a file with an "assistants" purpose
curl https://api.openai.com/v1/files \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -F purpose="assistants" \
  -F file="@/path/to/mydata.csv"

# Create an assistant using the file ID
curl https://api.openai.com/v1/assistants \
  -u :$OPENAI_API_KEY \
  -H 'Content-Type: application/json' \
  -H 'OpenAI-Beta: assistants=v2' \
  -d '{
    "instructions": "You are a personal math tutor. When asked a math question, write and run code to answer the question.",
    "tools": [{"type": "code_interpreter"}],
    "model": "gpt-4o",
    "tool_resources": {
      "code_interpreter": {
        "file_ids": ["file-BK7bzQj3FfZFXr7DbL6xJwfo"]
      }
    }
  }'
```

Files can also be passed at the Thread level. These files are only accessible in the specific Thread. Upload the File using the [File upload](/docs/api-reference/files/create) endpoint and then pass the File ID as part of the Message creation request:

```python
thread = client.beta.threads.create(
  messages=[
    {
      "role": "user",
      "content": "I need to solve the equation `3x + 11 = 14`. Can you help me?",
      "attachments": [
        {
          "file_id": file.id,
          "tools": [{"type": "code_interpreter"}]
        }
      ]
    }
  ]
)
```

```javascript
const thread = await openai.beta.threads.create({
  messages: [
    {
      "role": "user",
      "content": "I need to solve the equation `3x + 11 = 14`. Can you help me?",
      "attachments": [
        {
          file_id: file.id,
          tools: [{type: "code_interpreter"}]
        }
      ]
    }
  ]
});
```

```bash
curl https://api.openai.com/v1/threads/thread_abc123/messages \
  -u :$OPENAI_API_KEY \
  -H 'Content-Type: application/json' \
  -H 'OpenAI-Beta: assistants=v2' \
  -d '{
    "role": "user",
    "content": "I need to solve the equation `3x + 11 = 14`. Can you help me?",
    "attachments": [
      {
        "file_id": "file-ACq8OjcLQm2eIG0BvRM4z5qX",
        "tools": [{"type": "code_interpreter"}]
      }
    ]
  }'
```

Files have a maximum size of 512 MB. Code Interpreter supports a variety of file formats including `.csv`, `.pdf`, `.json` and many more. More details on the file extensions (and their corresponding MIME-types) supported can be found in the [Supported files](#supported-files) section below.

### Reading images and files generated by Code Interpreter

Code Interpreter in the API also outputs files, such as generating image diagrams, CSVs, and PDFs. There are two types of files that are generated:

1.  Images
2.  Data files (e.g. a `csv` file with data generated by the Assistant)

When Code Interpreter generates an image, you can look up and download this file in the `file_id` field of the Assistant Message response:

```json
{
	"id": "msg_abc123",
	"object": "thread.message",
	"created_at": 1698964262,
	"thread_id": "thread_abc123",
	"role": "assistant",
	"content": [
    {
      "type": "image_file",
      "image_file": {
        "file_id": "file-abc123"
      }
    }
  ]
  # ...
}
```

The file content can then be downloaded by passing the file ID to the Files API:

```python
from openai import OpenAI

client = OpenAI()

image_data = client.files.content("file-abc123")
image_data_bytes = image_data.read()

with open("./my-image.png", "wb") as file:
    file.write(image_data_bytes)
```

```javascript
import fs from "fs";
import OpenAI from "openai";

const openai = new OpenAI();

async function main() {
  const response = await openai.files.content("file-abc123");

  // Extract the binary data from the Response object
  const image_data = await response.arrayBuffer();

  // Convert the binary data to a Buffer
  const image_data_buffer = Buffer.from(image_data);

  // Save the image to a specific location
  fs.writeFileSync("./my-image.png", image_data_buffer);
}

main();
```

```bash
curl https://api.openai.com/v1/files/file-abc123/content \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  --output image.png
```

When Code Interpreter references a file path (e.g., ”Download this csv file”), file paths are listed as annotations. You can convert these annotations into links to download the file:

```json
{
  "id": "msg_abc123",
  "object": "thread.message",
  "created_at": 1699073585,
  "thread_id": "thread_abc123",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": {
        "value": "The rows of the CSV file have been shuffled and saved to a new CSV file. You can download the shuffled CSV file from the following link:\\n\\n[Download Shuffled CSV File](sandbox:/mnt/data/shuffled_file.csv)",
        "annotations": [
          {
            "type": "file_path",
            "text": "sandbox:/mnt/data/shuffled_file.csv",
            "start_index": 167,
            "end_index": 202,
            "file_path": {
              "file_id": "file-abc123"
            }
          }
          ...
```

### Input and output logs of Code Interpreter

By listing the steps of a Run that called Code Interpreter, you can inspect the code `input` and `outputs` logs of Code Interpreter:

```python
run_steps = client.beta.threads.runs.steps.list(
  thread_id=thread.id,
  run_id=run.id
)
```

```javascript
const runSteps = await openai.beta.threads.runs.steps.list(
  thread.id,
  run.id
);
```

```bash
curl https://api.openai.com/v1/threads/thread_abc123/runs/RUN_ID/steps \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "OpenAI-Beta: assistants=v2" \
```

```bash
{
  "object": "list",
  "data": [
    {
      "id": "step_abc123",
      "object": "thread.run.step",
      "type": "tool_calls",
      "run_id": "run_abc123",
      "thread_id": "thread_abc123",
      "status": "completed",
      "step_details": {
        "type": "tool_calls",
        "tool_calls": [
          {
            "type": "code",
            "code": {
              "input": "# Calculating 2 + 2\\nresult = 2 + 2\\nresult",
              "outputs": [
                {
                  "type": "logs",
                  "logs": "4"
                }
						...
 }
```

Supported files
---------------

|File format|MIME type|
|---|---|
|.c|text/x-c|
|.cs|text/x-csharp|
|.cpp|text/x-c++|
|.csv|text/csv|
|.doc|application/msword|
|.docx|application/vnd.openxmlformats-officedocument.wordprocessingml.document|
|.html|text/html|
|.java|text/x-java|
|.json|application/json|
|.md|text/markdown|
|.pdf|application/pdf|
|.php|text/x-php|
|.pptx|application/vnd.openxmlformats-officedocument.presentationml.presentation|
|.py|text/x-python|
|.py|text/x-script.python|
|.rb|text/x-ruby|
|.tex|text/x-tex|
|.txt|text/plain|
|.css|text/css|
|.js|text/javascript|
|.sh|application/x-sh|
|.ts|application/typescript|
|.csv|application/csv|
|.jpeg|image/jpeg|
|.jpg|image/jpeg|
|.gif|image/gif|
|.pkl|application/octet-stream|
|.png|image/png|
|.tar|application/x-tar|
|.xlsx|application/vnd.openxmlformats-officedocument.spreadsheetml.sheet|
|.xml|application/xml or "text/xml"|
|.zip|application/zip|

## Assistants Function Calling

===================================

Similar to the Chat Completions API, the Assistants API supports function calling. Function calling allows you to describe functions to the Assistants API and have it intelligently return the functions that need to be called along with their arguments.

Quickstart
----------

In this example, we'll create a weather assistant and define two functions, `get_current_temperature` and `get_rain_probability`, as tools that the Assistant can call. Depending on the user query, the model will invoke parallel function calling if using our latest models released on or after Nov 6, 2023. In our example that uses parallel function calling, we will ask the Assistant what the weather in San Francisco is like today and the chances of rain. We also show how to output the Assistant's response with streaming.

With the launch of Structured Outputs, you can now use the parameter `strict: true` when using function calling with the Assistants API. For more information, refer to the [Function calling guide](/docs/guides/function-calling#function-calling-with-structured-outputs). Please note that Structured Outputs are not supported in the Assistants API when using vision.

### Step 1: Define functions

When creating your assistant, you will first define the functions under the `tools` param of the assistant.

```python
from openai import OpenAI
client = OpenAI()
 
assistant = client.beta.assistants.create(
  instructions="You are a weather bot. Use the provided functions to answer questions.",
  model="gpt-4o",
  tools=[
    {
      "type": "function",
      "function": {
        "name": "get_current_temperature",
        "description": "Get the current temperature for a specific location",
        "parameters": {
          "type": "object",
          "properties": {
            "location": {
              "type": "string",
              "description": "The city and state, e.g., San Francisco, CA"
            },
            "unit": {
              "type": "string",
              "enum": ["Celsius", "Fahrenheit"],
              "description": "The temperature unit to use. Infer this from the user's location."
            }
          },
          "required": ["location", "unit"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "get_rain_probability",
        "description": "Get the probability of rain for a specific location",
        "parameters": {
          "type": "object",
          "properties": {
            "location": {
              "type": "string",
              "description": "The city and state, e.g., San Francisco, CA"
            }
          },
          "required": ["location"]
        }
      }
    }
  ]
)
```

```javascript
const assistant = await client.beta.assistants.create({
  model: "gpt-4o",
  instructions:
    "You are a weather bot. Use the provided functions to answer questions.",
  tools: [
    {
      type: "function",
      function: {
        name: "getCurrentTemperature",
        description: "Get the current temperature for a specific location",
        parameters: {
          type: "object",
          properties: {
            location: {
              type: "string",
              description: "The city and state, e.g., San Francisco, CA",
            },
            unit: {
              type: "string",
              enum: ["Celsius", "Fahrenheit"],
              description:
                "The temperature unit to use. Infer this from the user's location.",
            },
          },
          required: ["location", "unit"],
        },
      },
    },
    {
      type: "function",
      function: {
        name: "getRainProbability",
        description: "Get the probability of rain for a specific location",
        parameters: {
          type: "object",
          properties: {
            location: {
              type: "string",
              description: "The city and state, e.g., San Francisco, CA",
            },
          },
          required: ["location"],
        },
      },
    },
  ],
});
```

### Step 2: Create a Thread and add Messages

Create a Thread when a user starts a conversation and add Messages to the Thread as the user asks questions.

```python
thread = client.beta.threads.create()
message = client.beta.threads.messages.create(
  thread_id=thread.id,
  role="user",
  content="What's the weather in San Francisco today and the likelihood it'll rain?",
)
```

```javascript
const thread = await client.beta.threads.create();
const message = client.beta.threads.messages.create(thread.id, {
  role: "user",
  content: "What's the weather in San Francisco today and the likelihood it'll rain?",
});
```

### Step 3: Initiate a Run

When you initiate a Run on a Thread containing a user Message that triggers one or more functions, the Run will enter a `pending` status. After it processes, the run will enter a `requires_action` state which you can verify by checking the Run’s `status`. This indicates that you need to run tools and submit their outputs to the Assistant to continue Run execution. In our case, we will see two `tool_calls`, which indicates that the user query resulted in parallel function calling.

Note that a runs expire ten minutes after creation. Be sure to submit your tool outputs before the 10 min mark.

You will see two `tool_calls` within `required_action`, which indicates the user query triggered parallel function calling.

```json
{
  "id": "run_qJL1kI9xxWlfE0z1yfL0fGg9",
  ...
  "status": "requires_action",
  "required_action": {
    "submit_tool_outputs": {
      "tool_calls": [
        {
          "id": "call_FthC9qRpsL5kBpwwyw6c7j4k",
          "function": {
            "arguments": "{"location": "San Francisco, CA"}",
            "name": "get_rain_probability"
          },
          "type": "function"
        },
        {
          "id": "call_RpEDoB8O0FTL9JoKTuCVFOyR",
          "function": {
            "arguments": "{"location": "San Francisco, CA", "unit": "Fahrenheit"}",
            "name": "get_current_temperature"
          },
          "type": "function"
        }
      ]
    },
    ...
    "type": "submit_tool_outputs"
  }
}
```

Run object truncated here for readability

  

How you initiate a Run and submit `tool_calls` will differ depending on whether you are using streaming or not, although in both cases all `tool_calls` need to be submitted at the same time. You can then complete the Run by submitting the tool outputs from the functions you called. Pass each `tool_call_id` referenced in the `required_action` object to match outputs to each function call.

With streaming

For the streaming case, we create an EventHandler class to handle events in the response stream and submit all tool outputs at once with the “submit tool outputs stream” helper in the Python and Node SDKs.

```python
from typing_extensions import override
from openai import AssistantEventHandler
 
class EventHandler(AssistantEventHandler):
    @override
    def on_event(self, event):
      # Retrieve events that are denoted with 'requires_action'
      # since these will have our tool_calls
      if event.event == 'thread.run.requires_action':
        run_id = event.data.id  # Retrieve the run ID from the event data
        self.handle_requires_action(event.data, run_id)
 
    def handle_requires_action(self, data, run_id):
      tool_outputs = []
        
      for tool in data.required_action.submit_tool_outputs.tool_calls:
        if tool.function.name == "get_current_temperature":
          tool_outputs.append({"tool_call_id": tool.id, "output": "57"})
        elif tool.function.name == "get_rain_probability":
          tool_outputs.append({"tool_call_id": tool.id, "output": "0.06"})
        
      # Submit all tool_outputs at the same time
      self.submit_tool_outputs(tool_outputs, run_id)
 
    def submit_tool_outputs(self, tool_outputs, run_id):
      # Use the submit_tool_outputs_stream helper
      with client.beta.threads.runs.submit_tool_outputs_stream(
        thread_id=self.current_run.thread_id,
        run_id=self.current_run.id,
        tool_outputs=tool_outputs,
        event_handler=EventHandler(),
      ) as stream:
        for text in stream.text_deltas:
          print(text, end="", flush=True)
        print()
 
 
with client.beta.threads.runs.stream(
  thread_id=thread.id,
  assistant_id=assistant.id,
  event_handler=EventHandler()
) as stream:
  stream.until_done()
```

```javascript
class EventHandler extends EventEmitter {
  constructor(client) {
    super();
    this.client = client;
  }

  async onEvent(event) {
    try {
      console.log(event);
      // Retrieve events that are denoted with 'requires_action'
      // since these will have our tool_calls
      if (event.event === "thread.run.requires_action") {
        await this.handleRequiresAction(
          event.data,
          event.data.id,
          event.data.thread_id,
        );
      }
    } catch (error) {
      console.error("Error handling event:", error);
    }
  }

  async handleRequiresAction(data, runId, threadId) {
    try {
      const toolOutputs =
        data.required_action.submit_tool_outputs.tool_calls.map((toolCall) => {
          if (toolCall.function.name === "getCurrentTemperature") {
            return {
              tool_call_id: toolCall.id,
              output: "57",
            };
          } else if (toolCall.function.name === "getRainProbability") {
            return {
              tool_call_id: toolCall.id,
              output: "0.06",
            };
          }
        });
      // Submit all the tool outputs at the same time
      await this.submitToolOutputs(toolOutputs, runId, threadId);
    } catch (error) {
      console.error("Error processing required action:", error);
    }
  }

  async submitToolOutputs(toolOutputs, runId, threadId) {
    try {
      // Use the submitToolOutputsStream helper
      const stream = this.client.beta.threads.runs.submitToolOutputsStream(
        threadId,
        runId,
        { tool_outputs: toolOutputs },
      );
      for await (const event of stream) {
        this.emit("event", event);
      }
    } catch (error) {
      console.error("Error submitting tool outputs:", error);
    }
  }
}

const eventHandler = new EventHandler(client);
eventHandler.on("event", eventHandler.onEvent.bind(eventHandler));

const stream = await client.beta.threads.runs.stream(
  threadId,
  { assistant_id: assistantId },
  eventHandler,
);

for await (const event of stream) {
  eventHandler.emit("event", event);
}
```

Without streaming

Runs are asynchronous, which means you'll want to monitor their `status` by polling the Run object until a [terminal status](https://platform.openai.com/docs/assistants/deep-dive#runs-and-run-steps) is reached. For convenience, the 'create and poll' SDK helpers assist both in creating the run and then polling for its completion. Once the Run completes, you can list the Messages added to the Thread by the Assistant. Finally, you would retrieve all the `tool_outputs` from `required_action` and submit them at the same time to the 'submit tool outputs and poll' helper.

```python
run = client.beta.threads.runs.create_and_poll(
  thread_id=thread.id,
  assistant_id=assistant.id,
)
 
if run.status == 'completed':
  messages = client.beta.threads.messages.list(
    thread_id=thread.id
  )
  print(messages)
else:
  print(run.status)
 
# Define the list to store tool outputs
tool_outputs = []
 
# Loop through each tool in the required action section
for tool in run.required_action.submit_tool_outputs.tool_calls:
  if tool.function.name == "get_current_temperature":
    tool_outputs.append({
      "tool_call_id": tool.id,
      "output": "57"
    })
  elif tool.function.name == "get_rain_probability":
    tool_outputs.append({
      "tool_call_id": tool.id,
      "output": "0.06"
    })
 
# Submit all tool outputs at once after collecting them in a list
if tool_outputs:
  try:
    run = client.beta.threads.runs.submit_tool_outputs_and_poll(
      thread_id=thread.id,
      run_id=run.id,
      tool_outputs=tool_outputs
    )
    print("Tool outputs submitted successfully.")
  except Exception as e:
    print("Failed to submit tool outputs:", e)
else:
  print("No tool outputs to submit.")
 
if run.status == 'completed':
  messages = client.beta.threads.messages.list(
    thread_id=thread.id
  )
  print(messages)
else:
  print(run.status)
```

```javascript
const handleRequiresAction = async (run) => {
  // Check if there are tools that require outputs
  if (
    run.required_action &&
    run.required_action.submit_tool_outputs &&
    run.required_action.submit_tool_outputs.tool_calls
  ) {
    // Loop through each tool in the required action section
    const toolOutputs = run.required_action.submit_tool_outputs.tool_calls.map(
      (tool) => {
        if (tool.function.name === "getCurrentTemperature") {
          return {
            tool_call_id: tool.id,
            output: "57",
          };
        } else if (tool.function.name === "getRainProbability") {
          return {
            tool_call_id: tool.id,
            output: "0.06",
          };
        }
      },
    );

    // Submit all tool outputs at once after collecting them in a list
    if (toolOutputs.length > 0) {
      run = await client.beta.threads.runs.submitToolOutputsAndPoll(
        thread.id,
        run.id,
        { tool_outputs: toolOutputs },
      );
      console.log("Tool outputs submitted successfully.");
    } else {
      console.log("No tool outputs to submit.");
    }

    // Check status after submitting tool outputs
    return handleRunStatus(run);
  }
};

const handleRunStatus = async (run) => {
  // Check if the run is completed
  if (run.status === "completed") {
    let messages = await client.beta.threads.messages.list(thread.id);
    console.log(messages.data);
    return messages.data;
  } else if (run.status === "requires_action") {
    console.log(run.status);
    return await handleRequiresAction(run);
  } else {
    console.error("Run did not complete:", run);
  }
};

// Create and poll run
let run = await client.beta.threads.runs.createAndPoll(thread.id, {
  assistant_id: assistant.id,
});

handleRunStatus(run);
```

### Using Structured Outputs

When you enable [Structured Outputs](/docs/guides/structured-outputs) by supplying `strict: true`, the OpenAI API will pre-process your supplied schema on your first request, and then use this artifact to constrain the model to your schema.

```python
from openai import OpenAI
client = OpenAI()
 
assistant = client.beta.assistants.create(
  instructions="You are a weather bot. Use the provided functions to answer questions.",
  model="gpt-4o-2024-08-06",
  tools=[
    {
      "type": "function",
      "function": {
        "name": "get_current_temperature",
        "description": "Get the current temperature for a specific location",
        "parameters": {
          "type": "object",
          "properties": {
            "location": {
              "type": "string",
              "description": "The city and state, e.g., San Francisco, CA"
            },
            "unit": {
              "type": "string",
              "enum": ["Celsius", "Fahrenheit"],
              "description": "The temperature unit to use. Infer this from the user's location."
            }
          },
          "required": ["location", "unit"],
          "additionalProperties": False
        },
        "strict": True
      }
    },
    {
      "type": "function",
      "function": {
        "name": "get_rain_probability",
        "description": "Get the probability of rain for a specific location",
        "parameters": {
          "type": "object",
          "properties": {
            "location": {
              "type": "string",
              "description": "The city and state, e.g., San Francisco, CA"
            }
          },
          "required": ["location"],
          "additionalProperties": False
        },
        "strict": True
      }
    }
  ]
)
```

```javascript
const assistant = await client.beta.assistants.create({
  model: "gpt-4o-2024-08-06",
  instructions:
    "You are a weather bot. Use the provided functions to answer questions.",
  tools: [
    {
      type: "function",
      function: {
        name: "getCurrentTemperature",
        description: "Get the current temperature for a specific location",
        parameters: {
          type: "object",
          properties: {
            location: {
              type: "string",
              description: "The city and state, e.g., San Francisco, CA",
            },
            unit: {
              type: "string",
              enum: ["Celsius", "Fahrenheit"],
              description:
                "The temperature unit to use. Infer this from the user's location.",
            },
          },
          required: ["location", "unit"],
          additionalProperties: false
        },
        strict: true
      },
    },
    {
      type: "function",
      function: {
        name: "getRainProbability",
        description: "Get the probability of rain for a specific location",
        parameters: {
          type: "object",
          properties: {
            location: {
              type: "string",
              description: "The city and state, e.g., San Francisco, CA",
            },
          },
          required: ["location"],
          additionalProperties: false
        },
        strict: true
      },
    },
  ],
});
```

# Structured Outputs
====================

Introduction
------------

JSON is one of the most widely used formats in the world for applications to exchange data.

Structured Outputs is a feature that ensures the model will always generate responses that adhere to your supplied [JSON Schema](https://json-schema.org/overview/what-is-jsonschema), so you don't need to worry about the model omitting a required key, or hallucinating an invalid enum value.

Some benefits of Structured Outputs include:

1.  **Reliable type-safety:** No need to validate or retry incorrectly formatted responses
2.  **Explicit refusals:** Safety-based model refusals are now programmatically detectable
3.  **Simpler prompting:** No need for strongly worded prompts to achieve consistent formatting

In addition to supporting JSON Schema in the REST API, the OpenAI SDKs for [Python](https://github.com/openai/openai-python/blob/main/helpers.md#structured-outputs-parsing-helpers) and [JavaScript](https://github.com/openai/openai-node/blob/master/helpers.md#structured-outputs-parsing-helpers) also make it easy to define object schemas using [Pydantic](https://docs.pydantic.dev/latest/) and [Zod](https://zod.dev/) respectively. Below, you can see how to extract information from unstructured text that conforms to a schema defined in code.

Getting a structured response

```javascript
import OpenAI from "openai";
import { zodResponseFormat } from "openai/helpers/zod";
import { z } from "zod";

const openai = new OpenAI();

const CalendarEvent = z.object({
  name: z.string(),
  date: z.string(),
  participants: z.array(z.string()),
});

const completion = await openai.beta.chat.completions.parse({
  model: "gpt-4o-2024-08-06",
  messages: [
    { role: "system", content: "Extract the event information." },
    { role: "user", content: "Alice and Bob are going to a science fair on Friday." },
  ],
  response_format: zodResponseFormat(CalendarEvent, "event"),
});

const event = completion.choices[0].message.parsed;
```

```python
from pydantic import BaseModel
from openai import OpenAI

client = OpenAI()

class CalendarEvent(BaseModel):
    name: str
    date: str
    participants: list[str]

completion = client.beta.chat.completions.parse(
    model="gpt-4o-2024-08-06",
    messages=[
        {"role": "system", "content": "Extract the event information."},
        {"role": "user", "content": "Alice and Bob are going to a science fair on Friday."},
    ],
    response_format=CalendarEvent,
)

event = completion.choices[0].message.parsed
```

### Supported models

Structured Outputs are available in our [latest large language models](/docs/models), starting with GPT-4o:

*   `o3-mini-2025-1-31` and later
*   `o1-2024-12-17` and later
*   `gpt-4o-mini-2024-07-18` and later
*   `gpt-4o-2024-08-06` and later

Older models like `gpt-4-turbo` and earlier may use [JSON mode](#json-mode) instead.

When to use Structured Outputs via function calling vs via response\_format

-------------------------------------------------------------------------------

Structured Outputs is available in two forms in the OpenAI API:

1.  When using [function calling](/docs/guides/function-calling)
2.  When using a `json_schema` response format

Function calling is useful when you are building an application that bridges the models and functionality of your application.

For example, you can give the model access to functions that query a database in order to build an AI assistant that can help users with their orders, or functions that can interact with the UI.

Conversely, Structured Outputs via `response_format` are more suitable when you want to indicate a structured schema for use when the model responds to the user, rather than when the model calls a tool.

For example, if you are building a math tutoring application, you might want the assistant to respond to your user using a specific JSON Schema so that you can generate a UI that displays different parts of the model's output in distinct ways.

Put simply:

*   If you are connecting the model to tools, functions, data, etc. in your system, then you should use function calling
*   If you want to structure the model's output when it responds to the user, then you should use a structured `response_format`

The remainder of this guide will focus on non-function calling use cases in the Chat Completions API. To learn more about how to use Structured Outputs with function calling, check out the [Function Calling](/docs/guides/function-calling#function-calling-with-structured-outputs) guide.

### Structured Outputs vs JSON mode

Structured Outputs is the evolution of [JSON mode](#json-mode). While both ensure valid JSON is produced, only Structured Outputs ensure schema adherance. Both Structured Outputs and JSON mode are supported in the Chat Completions API, Assistants API, Fine-tuning API and Batch API.

We recommend always using Structured Outputs instead of JSON mode when possible.

However, Structured Outputs with `response_format: {type: "json_schema", ...}` is only supported with the `gpt-4o-mini`, `gpt-4o-mini-2024-07-18`, and `gpt-4o-2024-08-06` model snapshots and later.

||Structured Outputs|JSON Mode|
|---|---|---|
|Outputs valid JSON|Yes|Yes|
|Adheres to schema|Yes (see supported schemas)|No|
|Compatible models|gpt-4o-mini, gpt-4o-2024-08-06, and later|gpt-3.5-turbo, gpt-4-* and gpt-4o-* models|
|Enabling|response_format: { type: "json_schema", json_schema: {"strict": true, "schema": ...} }|response_format: { type: "json_object" }|

Examples
--------

Chain of thought

### Chain of thought

You can ask the model to output an answer in a structured, step-by-step way, to guide the user through the solution.

Structured Outputs for chain-of-thought math tutoring

```javascript
import OpenAI from "openai";
import { z } from "zod";
import { zodResponseFormat } from "openai/helpers/zod";

const openai = new OpenAI();

const Step = z.object({
  explanation: z.string(),
  output: z.string(),
});

const MathReasoning = z.object({
  steps: z.array(Step),
  final_answer: z.string(),
});

const completion = await openai.beta.chat.completions.parse({
  model: "gpt-4o-2024-08-06",
  messages: [
    { role: "system", content: "You are a helpful math tutor. Guide the user through the solution step by step." },
    { role: "user", content: "how can I solve 8x + 7 = -23" },
  ],
  response_format: zodResponseFormat(MathReasoning, "math_reasoning"),
});

const math_reasoning = completion.choices[0].message.parsed;
```

```python
from pydantic import BaseModel
from openai import OpenAI

client = OpenAI()

class Step(BaseModel):
    explanation: str
    output: str

class MathReasoning(BaseModel):
    steps: list[Step]
    final_answer: str

completion = client.beta.chat.completions.parse(
    model="gpt-4o-2024-08-06",
    messages=[
        {"role": "system", "content": "You are a helpful math tutor. Guide the user through the solution step by step."},
        {"role": "user", "content": "how can I solve 8x + 7 = -23"}
    ],
    response_format=MathReasoning,
)

math_reasoning = completion.choices[0].message.parsed
```

```bash
curl https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-2024-08-06",
    "messages": [
      {
        "role": "system",
        "content": "You are a helpful math tutor. Guide the user through the solution step by step."
      },
      {
        "role": "user",
        "content": "how can I solve 8x + 7 = -23"
      }
    ],
    "response_format": {
      "type": "json_schema",
      "json_schema": {
        "name": "math_reasoning",
        "schema": {
          "type": "object",
          "properties": {
            "steps": {
              "type": "array",
              "items": {
                "type": "object",
                "properties": {
                  "explanation": { "type": "string" },
                  "output": { "type": "string" }
                },
                "required": ["explanation", "output"],
                "additionalProperties": false
              }
            },
            "final_answer": { "type": "string" }
          },
          "required": ["steps", "final_answer"],
          "additionalProperties": false
        },
        "strict": true
      }
    }
  }'
```

#### Example response

```json
{
  "steps": [
    {
      "explanation": "Start with the equation 8x + 7 = -23.",
      "output": "8x + 7 = -23"
    },
    {
      "explanation": "Subtract 7 from both sides to isolate the term with the variable.",
      "output": "8x = -23 - 7"
    },
    {
      "explanation": "Simplify the right side of the equation.",
      "output": "8x = -30"
    },
    {
      "explanation": "Divide both sides by 8 to solve for x.",
      "output": "x = -30 / 8"
    },
    {
      "explanation": "Simplify the fraction.",
      "output": "x = -15 / 4"
    }
  ],
  "final_answer": "x = -15 / 4"
}
```

Structured data extraction

### Structured data extraction

You can define structured fields to extract from unstructured input data, such as reasearch papers.

Extracting data from research papers using Structured Outputs

```javascript
import OpenAI from "openai";
import { z } from "zod";
import { zodResponseFormat } from "openai/helpers/zod";

const openai = new OpenAI();

const ResearchPaperExtraction = z.object({
  title: z.string(),
  authors: z.array(z.string()),
  abstract: z.string(),
  keywords: z.array(z.string()),
});

const completion = await openai.beta.chat.completions.parse({
  model: "gpt-4o-2024-08-06",
  messages: [
    { role: "system", content: "You are an expert at structured data extraction. You will be given unstructured text from a research paper and should convert it into the given structure." },
    { role: "user", content: "..." },
  ],
  response_format: zodResponseFormat(ResearchPaperExtraction, "research_paper_extraction"),
});

const research_paper = completion.choices[0].message.parsed;
```

```python
from pydantic import BaseModel
from openai import OpenAI

client = OpenAI()

class ResearchPaperExtraction(BaseModel):
    title: str
    authors: list[str]
    abstract: str
    keywords: list[str]

completion = client.beta.chat.completions.parse(
    model="gpt-4o-2024-08-06",
    messages=[
        {"role": "system", "content": "You are an expert at structured data extraction. You will be given unstructured text from a research paper and should convert it into the given structure."},
        {"role": "user", "content": "..."}
    ],
    response_format=ResearchPaperExtraction,
)

research_paper = completion.choices[0].message.parsed
```

```bash
curl https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-2024-08-06",
    "messages": [
      {
        "role": "system",
        "content": "You are an expert at structured data extraction. You will be given unstructured text from a research paper and should convert it into the given structure."
      },
      {
        "role": "user",
        "content": "..."
      }
    ],
    "response_format": {
      "type": "json_schema",
      "json_schema": {
        "name": "research_paper_extraction",
        "schema": {
          "type": "object",
          "properties": {
            "title": { "type": "string" },
            "authors": {
              "type": "array",
              "items": { "type": "string" }
            },
            "abstract": { "type": "string" },
            "keywords": {
              "type": "array",
              "items": { "type": "string" }
            }
          },
          "required": ["title", "authors", "abstract", "keywords"],
          "additionalProperties": false
        },
        "strict": true
      }
    }
  }'
```

#### Example response

```json
{
  "title": "Application of Quantum Algorithms in Interstellar Navigation: A New Frontier",
  "authors": [
    "Dr. Stella Voyager",
    "Dr. Nova Star",
    "Dr. Lyra Hunter"
  ],
  "abstract": "This paper investigates the utilization of quantum algorithms to improve interstellar navigation systems. By leveraging quantum superposition and entanglement, our proposed navigation system can calculate optimal travel paths through space-time anomalies more efficiently than classical methods. Experimental simulations suggest a significant reduction in travel time and fuel consumption for interstellar missions.",
  "keywords": [
    "Quantum algorithms",
    "interstellar navigation",
    "space-time anomalies",
    "quantum superposition",
    "quantum entanglement",
    "space travel"
  ]
}
```

UI generation

### UI Generation

You can generate valid HTML by representing it as recursive data structures with constraints, like enums.

Generating HTML using Structured Outputs

```javascript
import OpenAI from "openai";
import { z } from "zod";
import { zodResponseFormat } from "openai/helpers/zod";

const openai = new OpenAI();

const UI = z.lazy(() =>
  z.object({
    type: z.enum(["div", "button", "header", "section", "field", "form"]),
    label: z.string(),
    children: z.array(UI),
    attributes: z.array(
      z.object({
        name: z.string(),
        value: z.string(),
      })
    ),
  })
);

const completion = await openai.beta.chat.completions.parse({
  model: "gpt-4o-2024-08-06",
  messages: [
    {
      role: "system",
      content: "You are a UI generator AI. Convert the user input into a UI.",
    },
    { role: "user", content: "Make a User Profile Form" },
  ],
  response_format: zodResponseFormat(UI, "ui"),
});

const ui = completion.choices[0].message.parsed;
```

```python
from enum import Enum
from typing import List
from pydantic import BaseModel
from openai import OpenAI

client = OpenAI()

class UIType(str, Enum):
    div = "div"
    button = "button"
    header = "header"
    section = "section"
    field = "field"
    form = "form"

class Attribute(BaseModel):
    name: str
    value: str

class UI(BaseModel):
    type: UIType
    label: str
    children: List["UI"] 
    attributes: List[Attribute]

UI.model_rebuild() # This is required to enable recursive types

class Response(BaseModel):
    ui: UI

completion = client.beta.chat.completions.parse(
    model="gpt-4o-2024-08-06",
    messages=[
        {"role": "system", "content": "You are a UI generator AI. Convert the user input into a UI."},
        {"role": "user", "content": "Make a User Profile Form"}
    ],
    response_format=Response,
)

ui = completion.choices[0].message.parsed
print(ui)
```

```bash
curl https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-2024-08-06",
    "messages": [
      {
        "role": "system",
        "content": "You are a UI generator AI. Convert the user input into a UI."
      },
      {
        "role": "user",
        "content": "Make a User Profile Form"
      }
    ],
    "response_format": {
      "type": "json_schema",
      "json_schema": {
        "name": "ui",
        "description": "Dynamically generated UI",
        "schema": {
          "type": "object",
          "properties": {
            "type": {
              "type": "string",
              "description": "The type of the UI component",
              "enum": ["div", "button", "header", "section", "field", "form"]
            },
            "label": {
              "type": "string",
              "description": "The label of the UI component, used for buttons or form fields"
            },
            "children": {
              "type": "array",
              "description": "Nested UI components",
              "items": {"$ref": "#"}
            },
            "attributes": {
              "type": "array",
              "description": "Arbitrary attributes for the UI component, suitable for any element",
              "items": {
                "type": "object",
                "properties": {
                  "name": {
                    "type": "string",
                    "description": "The name of the attribute, for example onClick or className"
                  },
                  "value": {
                    "type": "string",
                    "description": "The value of the attribute"
                  }
                },
                "required": ["name", "value"],
                "additionalProperties": false
              }
            }
          },
          "required": ["type", "label", "children", "attributes"],
          "additionalProperties": false
        },
        "strict": true
      }
    }
  }'
```

#### Example response

```json
{
    "type": "form",
    "label": "User Profile Form",
    "children": [
        {
            "type": "div",
            "label": "",
            "children": [
                {
                    "type": "field",
                    "label": "First Name",
                    "children": [],
                    "attributes": [
                        {
                            "name": "type",
                            "value": "text"
                        },
                        {
                            "name": "name",
                            "value": "firstName"
                        },
                        {
                            "name": "placeholder",
                            "value": "Enter your first name"
                        }
                    ]
                },
                {
                    "type": "field",
                    "label": "Last Name",
                    "children": [],
                    "attributes": [
                        {
                            "name": "type",
                            "value": "text"
                        },
                        {
                            "name": "name",
                            "value": "lastName"
                        },
                        {
                            "name": "placeholder",
                            "value": "Enter your last name"
                        }
                    ]
                }
            ],
            "attributes": []
        },
        {
            "type": "button",
            "label": "Submit",
            "children": [],
            "attributes": [
                {
                    "name": "type",
                    "value": "submit"
                }
            ]
        }
    ],
    "attributes": [
        {
            "name": "method",
            "value": "post"
        },
        {
            "name": "action",
            "value": "/submit-profile"
        }
    ]
}
```

Moderation

### Moderation

You can classify inputs on multiple categories, which is a common way of doing moderation.

Moderation using Structured Outputs

```javascript
import OpenAI from "openai";
import { z } from "zod";
import { zodResponseFormat } from "openai/helpers/zod";

const openai = new OpenAI();

const ContentCompliance = z.object({
  is_violating: z.boolean(),
  category: z.enum(["violence", "sexual", "self_harm"]).nullable(),
  explanation_if_violating: z.string().nullable(),
});

const completion = await openai.beta.chat.completions.parse({
  model: "gpt-4o-2024-08-06",
  messages: [
    { role: "system", content: "Determine if the user input violates specific guidelines and explain if they do." },
    { role: "user", content: "How do I prepare for a job interview?" },
  ],
  response_format: zodResponseFormat(ContentCompliance, "content_compliance"),
});

const compliance = completion.choices[0].message.parsed;
```

```python
from enum import Enum
from typing import Optional
from pydantic import BaseModel
from openai import OpenAI

client = OpenAI()

class Category(str, Enum):
    violence = "violence"
    sexual = "sexual"
    self_harm = "self_harm"

class ContentCompliance(BaseModel):
    is_violating: bool
    category: Optional[Category]
    explanation_if_violating: Optional[str]

completion = client.beta.chat.completions.parse(
    model="gpt-4o-2024-08-06",
    messages=[
        {"role": "system", "content": "Determine if the user input violates specific guidelines and explain if they do."},
        {"role": "user", "content": "How do I prepare for a job interview?"}
    ],
    response_format=ContentCompliance,
)

compliance = completion.choices[0].message.parsed
```

```bash
curl https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-2024-08-06",
    "messages": [
      {
        "role": "system",
        "content": "Determine if the user input violates specific guidelines and explain if they do."
      },
      {
        "role": "user",
        "content": "How do I prepare for a job interview?"
      }
    ],
    "response_format": {
      "type": "json_schema",
      "json_schema": {
        "name": "content_compliance",
        "description": "Determines if content is violating specific moderation rules",
        "schema": {
          "type": "object",
          "properties": {
            "is_violating": {
              "type": "boolean",
              "description": "Indicates if the content is violating guidelines"
            },
            "category": {
              "type": ["string", "null"],
              "description": "Type of violation, if the content is violating guidelines. Null otherwise.",
              "enum": ["violence", "sexual", "self_harm"]
            },
            "explanation_if_violating": {
              "type": ["string", "null"],
              "description": "Explanation of why the content is violating"
            }
          },
          "required": ["is_violating", "category", "explanation_if_violating"],
          "additionalProperties": false
        },
        "strict": true
      }
    }
  }'
```

#### Example response

```json
{
  "is_violating": false,
  "category": null,
  "explanation_if_violating": null
}
```

How to use Structured Outputs with response\_format

-------------------------------------------------------

You can use Structured Outputs with the new SDK helper to parse the model's output into your desired format, or you can specify the JSON schema directly.

**Note:** the first request you make with any schema will have additional latency as our API processes the schema, but subsequent requests with the same schema will not have additional latency.

SDK objects

Step 1: Define your object

First you must define an object or data structure to represent the JSON Schema that the model should be constrained to follow. See the [examples](/docs/guides/structured-outputs#examples) at the top of this guide for reference.

While Structured Outputs supports much of JSON Schema, some features are unavailable either for performance or technical reasons. See [here](/docs/guides/structured-outputs#supported-schemas) for more details.

For example, you can define an object like this:

```python
from pydantic import BaseModel

class Step(BaseModel):
    explanation: str
    output: str

class MathResponse(BaseModel):
    steps: list[Step]
    final_answer: str
```

```javascript
import { z } from "zod";
import { zodResponseFormat } from "openai/helpers/zod";

const Step = z.object({
  explanation: z.string(),
  output: z.string(),
});

const MathResponse = z.object({
  steps: z.array(Step),
  final_answer: z.string(),
});
```

#### Tips for your data structure

To maximize the quality of model generations, we recommend the following:

*   Name keys clearly and intuitively
*   Create clear titles and descriptions for important keys in your structure
*   Create and use evals to determine the structure that works best for your use case

Step 2: Supply your object in the API call

You can use the `parse` method to automatically parse the JSON response into the object you defined.

Under the hood, the SDK takes care of supplying the JSON schema corresponding to your data structure, and then parsing the response as an object.

```python
completion = client.beta.chat.completions.parse(
    model="gpt-4o-2024-08-06",
    messages=[
        {"role": "system", "content": "You are a helpful math tutor. Guide the user through the solution step by step."},
        {"role": "user", "content": "how can I solve 8x + 7 = -23"}
    ],
    response_format=MathResponse
  )
```

```javascript
const completion = await openai.beta.chat.completions.parse({
  model: "gpt-4o-2024-08-06",
  messages: [
    { role: "system", content: "You are a helpful math tutor. Guide the user through the solution step by step." },
    { role: "user", content: "how can I solve 8x + 7 = -23" },
  ],
  response_format: zodResponseFormat(MathResponse, "math_response"),
});
```

Step 3: Handle edge cases

In some cases, the model might not generate a valid response that matches the provided JSON schema.

This can happen in the case of a refusal, if the model refuses to answer for safety reasons, or if for example you reach a max tokens limit and the response is incomplete.

```javascript
try {
  const completion = await openai.chat.completions.create({
    model: "gpt-4o-2024-08-06",
    messages: [{
        role: "system",
        content: "You are a helpful math tutor. Guide the user through the solution step by step.",
      },
      {
        role: "user",
        content: "how can I solve 8x + 7 = -23"
      },
    ],
    store: true,
    response_format: {
      type: "json_schema",
      json_schema: {
        name: "math_response",
        schema: {
          type: "object",
          properties: {
            steps: {
              type: "array",
              items: {
                type: "object",
                properties: {
                  explanation: {
                    type: "string"
                  },
                  output: {
                    type: "string"
                  },
                },
                required: ["explanation", "output"],
                additionalProperties: false,
              },
            },
            final_answer: {
              type: "string"
            },
          },
          required: ["steps", "final_answer"],
          additionalProperties: false,
        },
        strict: true,
      },
    },
    max_tokens: 50,
  });

  if (completion.choices[0].finish_reason === "length") {
    // Handle the case where the model did not return a complete response
    throw new Error("Incomplete response");
  }

  const math_response = completion.choices[0].message;

  if (math_response.refusal) {
    // handle refusal
    console.log(math_response.refusal);
  } else if (math_response.content) {
    console.log(math_response.content);
  } else {
    throw new Error("No response content");
  }
} catch (e) {
  // Handle edge cases
  console.error(e);
}
```

```python
try:
    response = client.chat.completions.create(
        model="gpt-4o-2024-08-06",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful math tutor. Guide the user through the solution step by step.",
            },
            {"role": "user", "content": "how can I solve 8x + 7 = -23"},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "math_response",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "steps": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "explanation": {"type": "string"},
                                    "output": {"type": "string"},
                                },
                                "required": ["explanation", "output"],
                                "additionalProperties": False,
                            },
                        },
                        "final_answer": {"type": "string"},
                    },
                    "required": ["steps", "final_answer"],
                    "additionalProperties": False,
                },
            },
        },
        strict=True,
    )
except Exception as e:
    # handle errors like finish_reason, refusal, content_filter, etc.
    pass
```

Manual schema

Step 1: Define your schema

First you must design the JSON Schema that the model should be constrained to follow. See the [examples](/docs/guides/structured-outputs#examples) at the top of this guide for reference.

While Structured Outputs supports much of JSON Schema, some features are unavailable either for performance or technical reasons. See [here](/docs/guides/structured-outputs#supported-schemas) for more details.

#### Tips for your JSON Schema

To maximize the quality of model generations, we recommend the following:

*   Name keys clearly and intuitively
*   Create clear titles and descriptions for important keys in your structure
*   Create and use evals to determine the structure that works best for your use case

Step 2: Supply your schema in the API call

To use Structured Outputs, simply specify

```json
response_format: { "type": "json_schema", "json_schema": … , "strict": true }
```

For example:

```python
response = client.chat.completions.create(
    model="gpt-4o-2024-08-06",
    messages=[
        {"role": "system", "content": "You are a helpful math tutor. Guide the user through the solution step by step."},
        {"role": "user", "content": "how can I solve 8x + 7 = -23"}
    ],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "math_response",
            "schema": {
                "type": "object",
                "properties": {
                    "steps": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "explanation": {"type": "string"},
                                "output": {"type": "string"}
                            },
                            "required": ["explanation", "output"],
                            "additionalProperties": False
                        }
                    },
                    "final_answer": {"type": "string"}
                },
                "required": ["steps", "final_answer"],
                "additionalProperties": False
            },
            "strict": True
        }
    }
)

print(response.choices[0].message.content)
```

```javascript
const response = await openai.chat.completions.create({
    model: "gpt-4o-2024-08-06",
    messages: [
        { role: "system", content: "You are a helpful math tutor. Guide the user through the solution step by step." },
        { role: "user", content: "how can I solve 8x + 7 = -23" }
    ],
    store: true,
    response_format: {
        type: "json_schema",
        json_schema: {
            name: "math_response",
            schema: {
                type: "object",
                properties: {
                    steps: {
                        type: "array",
                        items: {
                            type: "object",
                            properties: {
                                explanation: { type: "string" },
                                output: { type: "string" }
                            },
                            required: ["explanation", "output"],
                            additionalProperties: false
                        }
                    },
                    final_answer: { type: "string" }
                },
                required: ["steps", "final_answer"],
                additionalProperties: false
            },
            strict: true
        }
    }
});

console.log(response.choices[0].message.content);
```

```bash
curl https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-2024-08-06",
    "messages": [
      {
        "role": "system",
        "content": "You are a helpful math tutor. Guide the user through the solution step by step."
      },
      {
        "role": "user",
        "content": "how can I solve 8x + 7 = -23"
      }
    ],
    "response_format": {
      "type": "json_schema",
      "json_schema": {
        "name": "math_response",
        "schema": {
          "type": "object",
          "properties": {
            "steps": {
              "type": "array",
              "items": {
                "type": "object",
                "properties": {
                  "explanation": { "type": "string" },
                  "output": { "type": "string" }
                },
                "required": ["explanation", "output"],
                "additionalProperties": false
              }
            },
            "final_answer": { "type": "string" }
          },
          "required": ["steps", "final_answer"],
          "additionalProperties": false
        },
        "strict": true
      }
    }
  }'
```

**Note:** the first request you make with any schema will have additional latency as our API processes the schema, but subsequent requests with the same schema will not have additional latency.

Step 3: Handle edge cases

In some cases, the model might not generate a valid response that matches the provided JSON schema.

This can happen in the case of a refusal, if the model refuses to answer for safety reasons, or if for example you reach a max tokens limit and the response is incomplete.

```javascript
try {
  const completion = await openai.chat.completions.create({
    model: "gpt-4o-2024-08-06",
    messages: [{
        role: "system",
        content: "You are a helpful math tutor. Guide the user through the solution step by step.",
      },
      {
        role: "user",
        content: "how can I solve 8x + 7 = -23"
      },
    ],
    store: true,
    response_format: {
      type: "json_schema",
      json_schema: {
        name: "math_response",
        schema: {
          type: "object",
          properties: {
            steps: {
              type: "array",
              items: {
                type: "object",
                properties: {
                  explanation: {
                    type: "string"
                  },
                  output: {
                    type: "string"
                  },
                },
                required: ["explanation", "output"],
                additionalProperties: false,
              },
            },
            final_answer: {
              type: "string"
            },
          },
          required: ["steps", "final_answer"],
          additionalProperties: false,
        },
        strict: true,
      },
    },
    max_tokens: 50,
  });

  if (completion.choices[0].finish_reason === "length") {
    // Handle the case where the model did not return a complete response
    throw new Error("Incomplete response");
  }

  const math_response = completion.choices[0].message;

  if (math_response.refusal) {
    // handle refusal
    console.log(math_response.refusal);
  } else if (math_response.content) {
    console.log(math_response.content);
  } else {
    throw new Error("No response content");
  }
} catch (e) {
  // Handle edge cases
  console.error(e);
}
```

```python
try:
    response = client.chat.completions.create(
        model="gpt-4o-2024-08-06",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful math tutor. Guide the user through the solution step by step.",
            },
            {"role": "user", "content": "how can I solve 8x + 7 = -23"},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "math_response",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "steps": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "explanation": {"type": "string"},
                                    "output": {"type": "string"},
                                },
                                "required": ["explanation", "output"],
                                "additionalProperties": False,
                            },
                        },
                        "final_answer": {"type": "string"},
                    },
                    "required": ["steps", "final_answer"],
                    "additionalProperties": False,
                },
            },
        },
        strict=True,
    )
except Exception as e:
    # handle errors like finish_reason, refusal, content_filter, etc.
    pass
```

Step 4: Use the generated structured data in a type-safe way

Typically, when using Structured Outputs you will have a type or class in the type-system of your programming language representing the JSON Schema as an object.

Once you have confirmed that you have received the JSON guaranteed to match the schema you requested, you can now safely parse it to the corresponding type.

For example:

```python
from pydantic import BaseModel, ValidationError
from typing import List

# Define types that match the JSON Schema using pydantic models
class Step(BaseModel):
    explanation: str
    output: str

class Solution(BaseModel):
    steps: List[Step]
    final_answer: str

...

try:
    # Parse and validate the response content
    solution = Solution.parse_raw(response.choices[0].message.content)
    print(solution)
except ValidationError as e:
    # Handle validation errors
    print(e.json())
```

```javascript
// Here we specify types in TypeScript that exactly match the JSON Schema we provided when calling the OpenAI API. Note that these *must* be kept in sync.

type Step = {
  explanation: string;
  output: string;
};

type Solution = {
  steps: Step[];
  final_answer: string;
};

...

// Now so long as the JSON Schema we created was exactly equivalent to our TypeScript types, this is type-safe
const solution = JSON.parse(response.choices[0].message.content)) as Solution
```

### 

Refusals with Structured Outputs

When using Structured Outputs with user-generated input, OpenAI models may occasionally refuse to fulfill the request for safety reasons. Since a refusal does not necessarily follow the schema you have supplied in `response_format`, the API response will include a new field called `refusal` to indicate that the model refused to fulfill the request.

When the `refusal` property appears in your output object, you might present the refusal in your UI, or include conditional logic in code that consumes the response to handle the case of a refused request.

```python
class Step(BaseModel):
    explanation: str
    output: str

class MathReasoning(BaseModel):
    steps: list[Step]
    final_answer: str

completion = client.beta.chat.completions.parse(
    model="gpt-4o-2024-08-06",
    messages=[
        {"role": "system", "content": "You are a helpful math tutor. Guide the user through the solution step by step."},
        {"role": "user", "content": "how can I solve 8x + 7 = -23"}
    ],
    response_format=MathReasoning,
)

math_reasoning = completion.choices[0].message

# If the model refuses to respond, you will get a refusal message
if (math_reasoning.refusal):
    print(math_reasoning.refusal)
else:
    print(math_reasoning.parsed)
```

```javascript
const Step = z.object({
  explanation: z.string(),
  output: z.string(),
});

const MathReasoning = z.object({
  steps: z.array(Step),
  final_answer: z.string(),
});

const completion = await openai.beta.chat.completions.parse({
  model: "gpt-4o-2024-08-06",
  messages: [
    { role: "system", content: "You are a helpful math tutor. Guide the user through the solution step by step." },
    { role: "user", content: "how can I solve 8x + 7 = -23" },
  ],
  response_format: zodResponseFormat(MathReasoning, "math_reasoning"),
});

const math_reasoning = completion.choices[0].message

// If the model refuses to respond, you will get a refusal message
if (math_reasoning.refusal) {
  console.log(math_reasoning.refusal);
} else {
  console.log(math_reasoning.parsed);
}
```

The API response from a refusal will look something like this:

```json
{
  "id": "chatcmpl-9nYAG9LPNonX8DAyrkwYfemr3C8HC",
  "object": "chat.completion",
  "created": 1721596428,
  "model": "gpt-4o-2024-08-06",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "refusal": "I'm sorry, I cannot assist with that request."
      },
      "logprobs": null,
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 81,
    "completion_tokens": 11,
    "total_tokens": 92,
    "completion_tokens_details": {
      "reasoning_tokens": 0,
      "accepted_prediction_tokens": 0,
      "rejected_prediction_tokens": 0
    }
  },
  "system_fingerprint": "fp_3407719c7f"
}
```

### 

Tips and best practices

#### Handling user-generated input

If your application is using user-generated input, make sure your prompt includes instructions on how to handle situations where the input cannot result in a valid response.

The model will always try to adhere to the provided schema, which can result in hallucinations if the input is completely unrelated to the schema.

You could include language in your prompt to specify that you want to return empty parameters, or a specific sentence, if the model detects that the input is incompatible with the task.

#### Handling mistakes

Structured Outputs can still contain mistakes. If you see mistakes, try adjusting your instructions, providing examples in the system instructions, or splitting tasks into simpler subtasks. Refer to the [prompt engineering guide](/docs/guides/prompt-engineering) for more guidance on how to tweak your inputs.

#### Avoid JSON schema divergence

To prevent your JSON Schema and corresponding types in your programming language from diverging, we strongly recommend using the native Pydantic/zod sdk support.

If you prefer to specify the JSON schema directly, you could add CI rules that flag when either the JSON schema or underlying data objects are edited, or add a CI step that auto-generates the JSON Schema from type definitions (or vice-versa).

Streaming
---------

You can use streaming to process model responses or function call arguments as they are being generated, and parse them as structured data.

That way, you don't have to wait for the entire response to complete before handling it. This is particularly useful if you would like to display JSON fields one by one, or handle function call arguments as soon as they are available.

We recommend relying on the SDKs to handle streaming with Structured Outputs. You can find an example of how to stream function call arguments without the SDK `stream` helper in the [function calling guide](/docs/guides/function-calling#advanced-usage).

Here is how you can stream a model response with the `stream` helper:

```python
from typing import List
from pydantic import BaseModel
from openai import OpenAI

class EntitiesModel(BaseModel):
    attributes: List[str]
    colors: List[str]
    animals: List[str]

client = OpenAI()

with client.beta.chat.completions.stream(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "Extract entities from the input text"},
        {
            "role": "user",
            "content": "The quick brown fox jumps over the lazy dog with piercing blue eyes",
        },
    ],
    response_format=EntitiesModel,
) as stream:
    for event in stream:
        if event.type == "content.delta":
            if event.parsed is not None:
                # Print the parsed data as JSON
                print("content.delta parsed:", event.parsed)
        elif event.type == "content.done":
            print("content.done")
        elif event.type == "error":
            print("Error in stream:", event.error)

final_completion = stream.get_final_completion()
print("Final completion:", final_completion)
```

```js
import OpenAI from "openai";
import { zodResponseFormat } from "openai/helpers/zod";
import { z } from "zod";
export const openai = new OpenAI();

const EntitiesSchema = z.object({
  attributes: z.array(z.string()),
  colors: z.array(z.string()),
  animals: z.array(z.string()),
});

const stream = openai.beta.chat.completions
  .stream({
    model: "gpt-4o",
    messages: [
      { role: "system", content: "Extract entities from the input text" },
      {
        role: "user",
        content:
          "The quick brown fox jumps over the lazy dog with piercing blue eyes",
      },
    ],
    response_format: zodResponseFormat(EntitiesSchema, "entities"),
  })
  .on("refusal.done", () => console.log("request refused"))
  .on("content.delta", ({ snapshot, parsed }) => {
    console.log("content:", snapshot);
    console.log("parsed:", parsed);
    console.log();
  })
  .on("content.done", (props) => {
    console.log(props);
  });

await stream.done();

const finalCompletion = await stream.finalChatCompletion();

console.log(finalCompletion);
```

You can also use the `stream` helper to parse function call arguments:

```python
from pydantic import BaseModel
import openai
from openai import OpenAI

class GetWeather(BaseModel):
    city: str
    country: str

client = OpenAI()

with client.beta.chat.completions.stream(
    model="gpt-4o",
    messages=[
        {
            "role": "user",
            "content": "What's the weather like in SF and London?",
        },
    ],
    tools=[
        openai.pydantic_function_tool(GetWeather, name="get_weather"),
    ],
    parallel_tool_calls=True,
) as stream:
    for event in stream:
        if event.type == "tool_calls.function.arguments.delta" or event.type == "tool_calls.function.arguments.done":
            print(event)

print(stream.get_final_completion())
```

```js
import { zodFunction } from "openai/helpers/zod";
import OpenAI from "openai/index";
import { z } from "zod";

const GetWeatherArgs = z.object({
  city: z.string(),
  country: z.string(),
});

const client = new OpenAI();

const stream = client.beta.chat.completions
  .stream({
    model: "gpt-4o",
    messages: [
      {
        role: "user",
        content: "What's the weather like in SF and London?",
      },
    ],
    tools: [zodFunction({ name: "get_weather", parameters: GetWeatherArgs })],
  })
  .on("tool_calls.function.arguments.delta", (props) =>
    console.log("tool_calls.function.arguments.delta", props)
  )
  .on("tool_calls.function.arguments.done", (props) =>
    console.log("tool_calls.function.arguments.done", props)
  )
  .on("refusal.delta", ({ delta }) => {
    process.stdout.write(delta);
  })
  .on("refusal.done", () => console.log("request refused"));

const completion = await stream.finalChatCompletion();

console.log("final completion:", completion);
```

Supported schemas
-----------------

Structured Outputs supports a subset of the [JSON Schema](https://json-schema.org/docs) language.

#### Supported types

The following types are supported for Structured Outputs:

*   String
*   Number
*   Boolean
*   Integer
*   Object
*   Array
*   Enum
*   anyOf

#### Root objects must not be `anyOf`

Note that the root level object of a schema must be an object, and not use `anyOf`. A pattern that appears in Zod (as one example) is using a discriminated union, which produces an `anyOf` at the top level. So code such as the following won't work:

```javascript
import { z } from 'zod';
import { zodResponseFormat } from 'openai/helpers/zod';

const BaseResponseSchema = z.object({ /* ... */ });
const UnsuccessfulResponseSchema = z.object({ /* ... */ });

const finalSchema = z.discriminatedUnion('status', [
    BaseResponseSchema,
    UnsuccessfulResponseSchema,
]);

// Invalid JSON Schema for Structured Outputs
const json = zodResponseFormat(finalSchema, 'final_schema');
```

#### All fields must be `required`

To use Structured Outputs, all fields or function parameters must be specified as `required`.

```json
{
    "name": "get_weather",
    "description": "Fetches the weather in the given location",
    "strict": true,
    "parameters": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "The location to get the weather for"
            },
            "unit": {
                "type": "string",
                "description": "The unit to return the temperature in",
                "enum": ["F", "C"]
            }
        },
        "additionalProperties": false,
        "required": ["location", "unit"]
    }
}
```

Although all fields must be required (and the model will return a value for each parameter), it is possible to emulate an optional parameter by using a union type with `null`.

```json
{
    "name": "get_weather",
    "description": "Fetches the weather in the given location",
    "strict": true,
    "parameters": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "The location to get the weather for"
            },
            "unit": {
                "type": ["string", "null"],
                "description": "The unit to return the temperature in",
                "enum": ["F", "C"]
            }
        },
        "additionalProperties": false,
        "required": [
            "location", "unit"
        ]
    }
}
```

#### Objects have limitations on nesting depth and size

A schema may have up to 100 object properties total, with up to 5 levels of nesting.

#### Limitations on total string size

In a schema, total string length of all property names, definition names, enum values, and const values cannot exceed 15,000 characters.

#### Limitations on enum size

A schema may have up to 500 enum values across all enum properties.

For a single enum property with string values, the total string length of all enum values cannot exceed 7,500 characters when there are more than 250 enum values.

#### `additionalProperties: false` must always be set in objects

`additionalProperties` controls whether it is allowable for an object to contain additional keys / values that were not defined in the JSON Schema.

Structured Outputs only supports generating specified keys / values, so we require developers to set `additionalProperties: false` to opt into Structured Outputs.

```json
{
    "name": "get_weather",
    "description": "Fetches the weather in the given location",
    "strict": true,
    "schema": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "The location to get the weather for"
            },
            "unit": {
                "type": "string",
                "description": "The unit to return the temperature in",
                "enum": ["F", "C"]
            }
        },
        "additionalProperties": false,
        "required": [
            "location", "unit"
        ]
    }
}
```

#### Key ordering

When using Structured Outputs, outputs will be produced in the same order as the ordering of keys in the schema.

#### Some type-specific keywords are not yet supported

Notable keywords not supported include:

*   **For strings:** `minLength`, `maxLength`, `pattern`, `format`
*   **For numbers:** `minimum`, `maximum`, `multipleOf`
*   **For objects:** `patternProperties`, `unevaluatedProperties`, `propertyNames`, `minProperties`, `maxProperties`
*   **For arrays:** `unevaluatedItems`, `contains`, `minContains`, `maxContains`, `minItems`, `maxItems`, `uniqueItems`

If you turn on Structured Outputs by supplying `strict: true` and call the API with an unsupported JSON Schema, you will receive an error.

#### For `anyOf`, the nested schemas must each be a valid JSON Schema per this subset

Here's an example supported anyOf schema:

```json
{
    "type": "object",
    "properties": {
        "item": {
            "anyOf": [
                {
                    "type": "object",
                    "description": "The user object to insert into the database",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "The name of the user"
                        },
                        "age": {
                            "type": "number",
                            "description": "The age of the user"
                        }
                    },
                    "additionalProperties": false,
                    "required": [
                        "name",
                        "age"
                    ]
                },
                {
                    "type": "object",
                    "description": "The address object to insert into the database",
                    "properties": {
                        "number": {
                            "type": "string",
                            "description": "The number of the address. Eg. for 123 main st, this would be 123"
                        },
                        "street": {
                            "type": "string",
                            "description": "The street name. Eg. for 123 main st, this would be main st"
                        },
                        "city": {
                            "type": "string",
                            "description": "The city of the address"
                        }
                    },
                    "additionalProperties": false,
                    "required": [
                        "number",
                        "street",
                        "city"
                    ]
                }
            ]
        }
    },
    "additionalProperties": false,
    "required": [
        "item"
    ]
}
```

#### Definitions are supported

You can use definitions to define subschemas which are referenced throughout your schema. The following is a simple example.

```json
{
    "type": "object",
    "properties": {
        "steps": {
            "type": "array",
            "items": {
                "$ref": "#/$defs/step"
            }
        },
        "final_answer": {
            "type": "string"
        }
    },
    "$defs": {
        "step": {
            "type": "object",
            "properties": {
                "explanation": {
                    "type": "string"
                },
                "output": {
                    "type": "string"
                }
            },
            "required": [
                "explanation",
                "output"
            ],
            "additionalProperties": false
        }
    },
    "required": [
        "steps",
        "final_answer"
    ],
    "additionalProperties": false
}
```

#### Recursive schemas are supported

Sample recursive schema using `#` to indicate root recursion.

```json
{
    "name": "ui",
    "description": "Dynamically generated UI",
    "strict": true,
    "schema": {
        "type": "object",
        "properties": {
            "type": {
                "type": "string",
                "description": "The type of the UI component",
                "enum": ["div", "button", "header", "section", "field", "form"]
            },
            "label": {
                "type": "string",
                "description": "The label of the UI component, used for buttons or form fields"
            },
            "children": {
                "type": "array",
                "description": "Nested UI components",
                "items": {
                    "$ref": "#"
                }
            },
            "attributes": {
                "type": "array",
                "description": "Arbitrary attributes for the UI component, suitable for any element",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "The name of the attribute, for example onClick or className"
                        },
                        "value": {
                            "type": "string",
                            "description": "The value of the attribute"
                        }
                    },
                    "additionalProperties": false,
                    "required": ["name", "value"]
                }
            }
        },
        "required": ["type", "label", "children", "attributes"],
        "additionalProperties": false
    }
}
```

Sample recursive schema using explicit recursion:

```json
{
    "type": "object",
    "properties": {
        "linked_list": {
            "$ref": "#/$defs/linked_list_node"
        }
    },
    "$defs": {
        "linked_list_node": {
            "type": "object",
            "properties": {
                "value": {
                    "type": "number"
                },
                "next": {
                    "anyOf": [
                        {
                            "$ref": "#/$defs/linked_list_node"
                        },
                        {
                            "type": "null"
                        }
                    ]
                }
            },
            "additionalProperties": false,
            "required": [
                "next",
                "value"
            ]
        }
    },
    "additionalProperties": false,
    "required": [
        "linked_list"
    ]
}
```

JSON mode
---------

JSON mode is a more basic version of the Structured Outputs feature. While JSON mode ensures that model output is valid JSON, Structured Outputs reliably matches the model's output to the schema you specify. We recommend you use Structured Outputs if it is supported for your use case.

When JSON mode is turned on, the model's output is ensured to be valid JSON, except for in some edge cases that you should detect and handle appropriately.

To turn on JSON mode with the Chat Completions or Assistants API you can set the `response_format` to `{ "type": "json_object" }`. If you are using function calling, JSON mode is always turned on.

Important notes:

*   When using JSON mode, you must always instruct the model to produce JSON via some message in the conversation, for example via your system message. If you don't include an explicit instruction to generate JSON, the model may generate an unending stream of whitespace and the request may run continually until it reaches the token limit. To help ensure you don't forget, the API will throw an error if the string "JSON" does not appear somewhere in the context.
*   JSON mode will not guarantee the output matches any specific schema, only that it is valid and parses without errors. You should use Structured Outputs to ensure it matches your schema, or if that is not possible, you should use a validation library and potentially retries to ensure that the output matches your desired schema.
*   Your application must detect and handle the edge cases that can result in the model output not being a complete JSON object (see below)

Handling edge cases

```javascript
const we_did_not_specify_stop_tokens = true;

try {
  const response = await openai.chat.completions.create({
    model: "gpt-3.5-turbo-0125",
    messages: [
      {
        role: "system",
        content: "You are a helpful assistant designed to output JSON.",
      },
      { role: "user", content: "Who won the world series in 2020? Please respond in the format {winner: ...}" },
    ],
    store: true,
    response_format: { type: "json_object" },
  });

  // Check if the conversation was too long for the context window, resulting in incomplete JSON 
  if (response.choices[0].message.finish_reason === "length") {
    // your code should handle this error case
  }

  // Check if the OpenAI safety system refused the request and generated a refusal instead
  if (response.choices[0].message[0].refusal) {
    // your code should handle this error case
    // In this case, the .content field will contain the explanation (if any) that the model generated for why it is refusing
    console.log(response.choices[0].message[0].refusal)
  }

  // Check if the model's output included restricted content, so the generation of JSON was halted and may be partial
  if (response.choices[0].message.finish_reason === "content_filter") {
    // your code should handle this error case
  }

  if (response.choices[0].message.finish_reason === "stop") {
    // In this case the model has either successfully finished generating the JSON object according to your schema, or the model generated one of the tokens you provided as a "stop token"

    if (we_did_not_specify_stop_tokens) {
      // If you didn't specify any stop tokens, then the generation is complete and the content key will contain the serialized JSON object
      // This will parse successfully and should now contain  {"winner": "Los Angeles Dodgers"}
      console.log(JSON.parse(response.choices[0].message.content))
    } else {
      // Check if the response.choices[0].message.content ends with one of your stop tokens and handle appropriately
    }
  }
} catch (e) {
  // Your code should handle errors here, for example a network error calling the API
  console.error(e)
}
```

```python
we_did_not_specify_stop_tokens = True

try:
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-0125",
        messages=[
            {"role": "system", "content": "You are a helpful assistant designed to output JSON."},
            {"role": "user", "content": "Who won the world series in 2020? Please respond in the format {winner: ...}"}
        ],
        response_format={"type": "json_object"}
    )

    # Check if the conversation was too long for the context window, resulting in incomplete JSON 
    if response.choices[0].message.finish_reason == "length":
        # your code should handle this error case
        pass

    # Check if the OpenAI safety system refused the request and generated a refusal instead
    if response.choices[0].message[0].get("refusal"):
        # your code should handle this error case
        # In this case, the .content field will contain the explanation (if any) that the model generated for why it is refusing
        print(response.choices[0].message[0]["refusal"])

    # Check if the model's output included restricted content, so the generation of JSON was halted and may be partial
    if response.choices[0].message.finish_reason == "content_filter":
        # your code should handle this error case
        pass

    if response.choices[0].message.finish_reason == "stop":
        # In this case the model has either successfully finished generating the JSON object according to your schema, or the model generated one of the tokens you provided as a "stop token"

        if we_did_not_specify_stop_tokens:
            # If you didn't specify any stop tokens, then the generation is complete and the content key will contain the serialized JSON object
            # This will parse successfully and should now contain  "{"winner": "Los Angeles Dodgers"}"
            print(response.choices[0].message.content)
        else:
            # Check if the response.choices[0].message.content ends with one of your stop tokens and handle appropriately
            pass
except Exception as e:
    # Your code should handle errors here, for example a network error calling the API
    print(e)
```

# Function calling
==================

Enable models to fetch data and take actions.

**Function calling** provides a powerful and flexible way for OpenAI models to interface with your code or external services, and has two primary use cases:

|||
|---|---|
|Fetching Data|Retrieve up-to-date information to incorporate into the model's response (RAG). Useful for searching knowledge bases and retrieving specific data from APIs (e.g. current weather data).|
|Taking Action|Perform actions like submitting a form, calling APIs, modifying application state (UI/frontend or backend), or taking agentic workflow actions (like handing off the conversation).|

If you only want the model to produce JSON, see our docs on [structured outputs](/docs/guides/structured-outputs).

Get weather

Function calling example with get\_weather function

```python
from openai import OpenAI

client = OpenAI()

tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get current temperature for a given location.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City and country e.g. Bogotá, Colombia"
                }
            },
            "required": [
                "location"
            ],
            "additionalProperties": False
        },
        "strict": True
    }
}]

completion = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "What is the weather like in Paris today?"}],
    tools=tools
)

print(completion.choices[0].message.tool_calls)
```

```javascript
import { OpenAI } from "openai";

const openai = new OpenAI();

const tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get current temperature for a given location.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City and country e.g. Bogotá, Colombia"
                }
            },
            "required": [
                "location"
            ],
            "additionalProperties": false
        },
        "strict": true
    }
}];

const completion = await openai.chat.completions.create({
    model: "gpt-4o",
    messages: [{ role: "user", content: "What is the weather like in Paris today?" }],
    tools,
    store: true,
});

console.log(completion.choices[0].message.tool_calls);
```

```bash
curl https://api.openai.com/v1/chat/completions \
-H "Content-Type: application/json" \
-H "Authorization: Bearer $OPENAI_API_KEY" \
-d '{
    "model": "gpt-4o",
    "messages": [
        {
            "role": "user",
            "content": "What is the weather like in Paris today?"
        }
    ],
    "tools": [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get current temperature for a given location.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "City and country e.g. Bogotá, Colombia"
                        }
                    },
                    "required": [
                        "location"
                    ],
                    "additionalProperties": false
                },
                "strict": true
            }
        }
    ]
}'
```

Output

```json
[{
    "id": "call_12345xyz",
    "type": "function",
    "function": {
        "name": "get_weather",
        "arguments": "{\"location\":\"Paris, France\"}"
    }
}]
```

Send email

Function calling example with send\_email function

```python
from openai import OpenAI

client = OpenAI()

tools = [{
    "type": "function",
    "function": {
        "name": "send_email",
        "description": "Send an email to a given recipient with a subject and message.",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "The recipient email address."
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject line."
                },
                "body": {
                    "type": "string",
                    "description": "Body of the email message."
                }
            },
            "required": [
                "to",
                "subject",
                "body"
            ],
            "additionalProperties": False
        },
        "strict": True
    }
}]

completion = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Can you send an email to ilan@example.com and katia@example.com saying hi?"}],
    tools=tools
)

print(completion.choices[0].message.tool_calls)
```

```javascript
import { OpenAI } from "openai";

const openai = new OpenAI();

const tools = [{
    "type": "function",
    "function": {
        "name": "send_email",
        "description": "Send an email to a given recipient with a subject and message.",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "The recipient email address."
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject line."
                },
                "body": {
                    "type": "string",
                    "description": "Body of the email message."
                }
            },
            "required": [
                "to",
                "subject",
                "body"
            ],
            "additionalProperties": false
        },
        "strict": true
    }
}];

const completion = await openai.chat.completions.create({
    model: "gpt-4o",
    messages: [{ role: "user", content: "Can you send an email to ilan@example.com and katia@example.com saying hi?" }],
    tools,
    store: true,
});

console.log(completion.choices[0].message.tool_calls);
```

```bash
curl https://api.openai.com/v1/chat/completions \
-H "Content-Type: application/json" \
-H "Authorization: Bearer $OPENAI_API_KEY" \
-d '{
    "model": "gpt-4o",
    "messages": [
        {
            "role": "user",
            "content": "Can you send an email to ilan@example.com and katia@example.com saying hi?"
        }
    ],
    "tools": [
        {
            "type": "function",
            "function": {
                "name": "send_email",
                "description": "Send an email to a given recipient with a subject and message.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "to": {
                            "type": "string",
                            "description": "The recipient email address."
                        },
                        "subject": {
                            "type": "string",
                            "description": "Email subject line."
                        },
                        "body": {
                            "type": "string",
                            "description": "Body of the email message."
                        }
                    },
                    "required": [
                        "to",
                        "subject",
                        "body"
                    ],
                    "additionalProperties": false
                },
                "strict": true
            }
        }
    ]
}'
```

Output

```json
[
    {
        "id": "call_9876abc",
        "type": "function",
        "function": {
            "name": "send_email",
            "arguments": "{\"to\":\"ilan@example.com\",\"subject\":\"Hello!\",\"body\":\"Just wanted to say hi\"}"
        }
    },
    {
        "id": "call_9876abc",
        "type": "function",
        "function": {
            "name": "send_email",
            "arguments": "{\"to\":\"katia@example.com\",\"subject\":\"Hello!\",\"body\":\"Just wanted to say hi\"}"
        }
    }
]
```

Search knowledge base

Function calling example with search\_knowledge\_base function

```python
from openai import OpenAI

client = OpenAI()

tools = [{
    "type": "function",
    "function": {
        "name": "search_knowledge_base",
        "description": "Query a knowledge base to retrieve relevant info on a topic.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The user question or search query."
                },
                "options": {
                    "type": "object",
                    "properties": {
                        "num_results": {
                            "type": "number",
                            "description": "Number of top results to return."
                        },
                        "domain_filter": {
                            "type": [
                                "string",
                                "null"
                            ],
                            "description": "Optional domain to narrow the search (e.g. 'finance', 'medical'). Pass null if not needed."
                        },
                        "sort_by": {
                            "type": [
                                "string",
                                "null"
                            ],
                            "enum": [
                                "relevance",
                                "date",
                                "popularity",
                                "alphabetical"
                            ],
                            "description": "How to sort results. Pass null if not needed."
                        }
                    },
                    "required": [
                        "num_results",
                        "domain_filter",
                        "sort_by"
                    ],
                    "additionalProperties": False
                }
            },
            "required": [
                "query",
                "options"
            ],
            "additionalProperties": False
        },
        "strict": True
    }
}]

completion = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Can you find information about ChatGPT in the AI knowledge base?"}],
    tools=tools
)

print(completion.choices[0].message.tool_calls)
```

```javascript
import { OpenAI } from "openai";

const openai = new OpenAI();

const tools = [{
    "type": "function",
    "function": {
        "name": "search_knowledge_base",
        "description": "Query a knowledge base to retrieve relevant info on a topic.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The user question or search query."
                },
                "options": {
                    "type": "object",
                    "properties": {
                        "num_results": {
                            "type": "number",
                            "description": "Number of top results to return."
                        },
                        "domain_filter": {
                            "type": [
                                "string",
                                "null"
                            ],
                            "description": "Optional domain to narrow the search (e.g. 'finance', 'medical'). Pass null if not needed."
                        },
                        "sort_by": {
                            "type": [
                                "string",
                                "null"
                            ],
                            "enum": [
                                "relevance",
                                "date",
                                "popularity",
                                "alphabetical"
                            ],
                            "description": "How to sort results. Pass null if not needed."
                        }
                    },
                    "required": [
                        "num_results",
                        "domain_filter",
                        "sort_by"
                    ],
                    "additionalProperties": false
                }
            },
            "required": [
                "query",
                "options"
            ],
            "additionalProperties": false
        },
        "strict": true
    }
}];

const completion = await openai.chat.completions.create({
    model: "gpt-4o",
    messages: [{ role: "user", content: "Can you find information about ChatGPT in the AI knowledge base?" }],
    tools,
    store: true,
});

console.log(completion.choices[0].message.tool_calls);
```

```bash
curl https://api.openai.com/v1/chat/completions \
-H "Content-Type: application/json" \
-H "Authorization: Bearer $OPENAI_API_KEY" \
-d '{
    "model": "gpt-4o",
    "messages": [
        {
            "role": "user",
            "content": "Can you find information about ChatGPT in the AI knowledge base?"
        }
    ],
    "tools": [
        {
            "type": "function",
            "function": {
                "name": "search_knowledge_base",
                "description": "Query a knowledge base to retrieve relevant info on a topic.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The user question or search query."
                        },
                        "options": {
                            "type": "object",
                            "properties": {
                                "num_results": {
                                    "type": "number",
                                    "description": "Number of top results to return."
                                },
                                "domain_filter": {
                                    "type": [
                                        "string",
                                        "null"
                                    ],
                                    "description": "Optional domain to narrow the search (e.g. 'finance', 'medical'). Pass null if not needed."
                                },
                                "sort_by": {
                                    "type": [
                                        "string",
                                        "null"
                                    ],
                                    "enum": [
                                        "relevance",
                                        "date",
                                        "popularity",
                                        "alphabetical"
                                    ],
                                    "description": "How to sort results. Pass null if not needed."
                                }
                            },
                            "required": [
                                "num_results",
                                "domain_filter",
                                "sort_by"
                            ],
                            "additionalProperties": false
                        }
                    },
                    "required": [
                        "query",
                        "options"
                    ],
                    "additionalProperties": false
                },
                "strict": true
            }
        }
    ]
}'
```

Output

```json
[{
    "id": "call_4567xyz",
    "type": "function",
    "function": {
        "name": "search_knowledge_base",
        "arguments": "{\"query\":\"What is ChatGPT?\",\"options\":{\"num_results\":3,\"domain_filter\":null,\"sort_by\":\"relevance\"}}"
    }
}]
```

Experiment with function calling and [generate function schemas](/docs/guides/prompt-generation) in the [Playground](/playground)!

Overview
--------

You can extend the capabilities of OpenAI models by giving them access to `tools`, which can have one of two forms:

|||
|---|---|
|Function Calling|Developer-defined code.|
|Hosted Tools|OpenAI-built tools. (e.g. file search, code interpreter)Only available in the Assistants API.|

This guide will cover how you can give the model access to your own functions through **function calling**. Based on the system prompt and messages, the model may decide to call these functions — **instead of (or in addition to) generating text or audio**.

You'll then execute the function code, send back the results, and the model will incorporate them into its final response.

![Function Calling Diagram Steps](https://cdn.openai.com/API/docs/images/function-calling-diagram-steps.png)

### Sample function

Let's look at the steps to allow a model to use a real `get_weather` function defined below:

Sample get\_weather function implemented in your codebase

```python
import requests

def get_weather(latitude, longitude):
    response = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m,wind_speed_10m&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m")
    data = response.json()
    return data['current']['temperature_2m']
```

```javascript
async function getWeather(latitude, longitude) {
    const response = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${latitude}&longitude=${longitude}&current=temperature_2m,wind_speed_10m&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m`);
    const data = await response.json();
    return data.current.temperature_2m;
}
```

Unlike the diagram earlier, this function expects precise `latitude` and `longitude` instead of a general `location` parameter. (However, our models can automatically determine the coordinates for many locations!)

### Function calling steps

*   **Call model with [functions defined](#defining-functions)** – along with your system and user messages.
    

Step 1: Call model with get\_weather tool defined

```python
from openai import OpenAI
import json

client = OpenAI()

tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get current temperature for provided coordinates in celsius.",
        "parameters": {
            "type": "object",
            "properties": {
                "latitude": {"type": "number"},
                "longitude": {"type": "number"}
            },
            "required": ["latitude", "longitude"],
            "additionalProperties": False
        },
        "strict": True
    }
}]

messages = [{"role": "user", "content": "What's the weather like in Paris today?"}]

completion = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    tools=tools,
)
```

```javascript
import { OpenAI } from "openai";

const openai = new OpenAI();

const tools = [{
    type: "function",
    function: {
        name: "get_weather",
        description: "Get current temperature for provided coordinates in celsius.",
        parameters: {
            type: "object",
            properties: {
                latitude: { type: "number" },
                longitude: { type: "number" }
            },
            required: ["latitude", "longitude"],
            additionalProperties: false
        },
        strict: true
    }
}];

const messages = [
    {
        role: "user",
        content: "What's the weather like in Paris today?"
    }
];

const completion = await openai.chat.completions.create({
    model: "gpt-4o",
    messages,
    tools,
    store: true,
});
```

*   **Model decides to call function(s)** – model returns the **name** and **input arguments**.
    

completion.choices\[0\].message.tool\_calls

```json
[{
    "id": "call_12345xyz",
    "type": "function",
    "function": {
      "name": "get_weather",
      "arguments": "{\"latitude\":48.8566,\"longitude\":2.3522}"
    }
}]
```

*   **Execute function code** – parse the model's response and [handle function calls](#handling-function-calls).
    

Step 3: Execute get\_weather function

```python
tool_call = completion.choices[0].message.tool_calls[0]
args = json.loads(tool_call.function.arguments)

result = get_weather(args["latitude"], args["longitude"])
```

```javascript
const toolCall = completion.choices[0].message.tool_calls[0];
const args = JSON.parse(toolCall.function.arguments);

const result = await get_weather(args.latitude, args.longitude);
```

*   **Supply model with results** – so it can incorporate them into its final response.
    

Step 4: Supply result and call model again

```python
messages.append(completion.choices[0].message)  # append model's function call message
messages.append({                               # append result message
    "role": "tool",
    "tool_call_id": tool_call.id,
    "content": result
})

completion_2 = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    tools=tools,
)
```

```javascript
messages.push(completion.choices[0].message); // append model's function call message
messages.push({                               // append result message
    role: "tool",
    tool_call_id: toolCall.id,
    content: result.toString()
});

const completion2 = await openai.chat.completions.create({
    model: "gpt-4o",
    messages,
    tools,
    store: true,
});

console.log(completion2.choices[0].message.content);
```

*   **Model responds** – incorporating the result in its output.
    

completion\_2.choices\[0\].message.content

```json
"The current temperature in Paris is 14°C (57.2°F)."
```

Defining functions
------------------

Functions can be set in the `tools` parameter of each API request inside a `function` object.

A function is defined by its schema, which informs the model what it does and what input arguments it expects. It comprises the following fields:

|Field|Description|
|---|---|
|name|The function's name (e.g. get_weather)|
|description|Details on when and how to use the function|
|parameters|JSON schema defining the function's input arguments|

Take a look at this example or generate your own below (or in our [Playground](/playground)).

Generate

Example function schema

```json
{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Retrieves current weather for the given location.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City and country e.g. Bogotá, Colombia"
                },
                "units": {
                    "type": "string",
                    "enum": [
                        "celsius",
                        "fahrenheit"
                    ],
                    "description": "Units the temperature will be returned in."
                }
            },
            "required": [
                "location",
                "units"
            ],
            "additionalProperties": false
        },
        "strict": true
    }
}
```

Because the `parameters` are defined by a [JSON schema](https://json-schema.org/), you can leverage many of its rich features like property types, enums, descriptions, nested objects, and, recursive objects.

(Optional) Function calling wth pydantic and zod

While we encourage you to define your function schemas directly, our SDKs have helpers to convert `pydantic` and `zod` objects into schemas. Not all `pydantic` and `zod` features are supported.

Define objects to represent function schema

```python
from openai import OpenAI, pydantic_function_tool
from pydantic import BaseModel, Field

client = OpenAI()

class GetWeather(BaseModel):
    location: str = Field(
        ...,
        description="City and country e.g. Bogotá, Colombia"
    )

tools = [pydantic_function_tool(GetWeather)]

completion = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "What's the weather like in Paris today?"}],
    tools=tools
)

print(completion.choices[0].message.tool_calls)
```

```javascript
import OpenAI from "openai";
import { z } from "zod";
import { zodFunction } from "openai/helpers/zod";

const openai = new OpenAI();

const GetWeatherParameters = z.object({
  location: z.string().describe("City and country e.g. Bogotá, Colombia"),
});

const tools = [
  zodFunction({ name: "getWeather", parameters: GetWeatherParameters }),
];

const messages = [
  { role: "user", content: "What's the weather like in Paris today?" },
];

const response = await openai.chat.completions.create({
  model: "gpt-4o",
  messages,
  tools,
  store: true,
});

console.log(response.choices[0].message.tool_calls);
```

### Best practices for defining functions

1.  **Write clear and detailed function names, parameter descriptions, and instructions.**
    
    *   **Explicitly describe the purpose of the function and each parameter** (and its format), and what the output represents.
    *   **Use the system prompt to describe when (and when not) to use each function.** Generally, tell the model _exactly_ what to do.
    *   **Include examples and edge cases**, especially to rectify any recurring failures. (**Note:** Adding examples may hurt performance for [reasoning models](/docs/guides/reasoning).)
2.  **Apply software engineering best practices.**
    
    *   **Make the functions obvious and intuitive**. ([principle of least surprise](https://en.wikipedia.org/wiki/Principle_of_least_astonishment))
    *   **Use enums** and object structure to make invalid states unrepresentable. (e.g. `toggle_light(on: bool, off: bool)` allows for invalid calls)
    *   **Pass the intern test.** Can an intern/human correctly use the function given nothing but what you gave the model? (If not, what questions do they ask you? Add the answers to the prompt.)
3.  **Offload the burden from the model and use code where possible.**
    
    *   **Don't make the model fill arguments you already know.** For example, if you already have an `order_id` based on a previous menu, don't have an `order_id` param – instead, have no params `submit_refund()` and pass the `order_id` with code.
    *   **Combine functions that are always called in sequence.** For example, if you always call `mark_location()` after `query_location()`, just move the marking logic into the query function call.
4.  **Keep the number of functions small for higher accuracy.**
    
    *   **Evaluate your performance** with different numbers of functions.
    *   **Aim for fewer than 20 functions** at any one time, though this is just a soft suggestion.
5.  **Leverage OpenAI resources.**
    
    *   **Generate and iterate on function schemas** in the [Playground](/playground).
    *   **Consider [fine-tuning](https://platform.openai.com/docs/guides/fine-tuning) to increase function calling accuracy** for large numbers of functions or difficult tasks. ([cookbook](https://cookbook.openai.com/examples/fine_tuning_for_function_calling))

### Token Usage

Under the hood, functions are injected into the system message in a syntax the model has been trained on. This means functions count against the model's context limit and are billed as input tokens. If you run into token limits, we suggest limiting the number of functions or the length of the descriptions you provide for function parameters.

It is also possible to use [fine-tuning](/docs/guides/fine-tuning#fine-tuning-examples) to reduce the number of tokens used if you have many functions defined in your tools specification.

Handling function calls
-----------------------

When the model calls a function, you must execute it and return the result. Since model responses can include zero, one, or multiple calls, it is best practice to assume there are several.

The response has an array of `tool_calls`, each with an `id` (used later to submit the function result) and a `function` containing a `name` and JSON-encoded `arguments`.

Sample response with multiple function calls

```json
[
    {
        "id": "call_12345xyz",
        "type": "function",
        "function": {
            "name": "get_weather",
            "arguments": "{\"location\":\"Paris, France\"}"
        }
    },
    {
        "id": "call_67890abc",
        "type": "function",
        "function": {
            "name": "get_weather",
            "arguments": "{\"location\":\"Bogotá, Colombia\"}"
        }
    },
    {
        "id": "call_99999def",
        "type": "function",
        "function": {
            "name": "send_email",
            "arguments": "{\"to\":\"bob@email.com\",\"body\":\"Hi bob\"}"
        }
    }
]
```

Execute function calls and append results

```python
for tool_call in completion.choices[0].message.tool_calls:
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)

    result = call_function(name, args)
    messages.append({
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": result
    })
```

```javascript
for (const toolCall of completion.choices[0].message.tool_calls) {
    const name = toolCall.function.name;
    const args = JSON.parse(toolCall.function.arguments);

    const result = callFunction(name, args);
    messages.push({
        role: "tool",
        tool_call_id: toolCall.id,
        content: result.toString()
    });
}
```

In the example above, we have a hypothetical `call_function` to route each call. Here’s a possible implementation:

Execute function calls and append results

```python
def call_function(name, args):
    if name == "get_weather":
        return get_weather(**args)
    if name == "send_email":
        return send_email(**args)
```

```javascript
const callFunction = async (name, args) => {
    if (name === "get_weather") {
        return getWeather(args.latitude, args.longitude);
    }
    if (name === "send_email") {
        return sendEmail(args.to, args.body);
    }
};
```

### Formatting results

A result must be a string, but the format is up to you (JSON, error codes, plain text, etc.). The model will interpret that string as needed.

If your function has no return value (e.g. `send_email`), simply return a string to indicate success or failure. (e.g. `"success"`)

### Incorporating results into response

After appending the results to your `messages`, you can send them back to the model to get a final response.

Send results back to model

```python
completion = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    tools=tools,
)
```

```javascript
const completion = await openai.chat.completions.create({
    model: "gpt-4o",
    messages,
    tools,
    store: true,
});
```

Final response

```json
"It's about 15°C in Paris, 18°C in Bogotá, and I've sent that email to Bob."
```

Additional configurations
-------------------------

### Tool choice

By default the model will determine when and how many tools to use. You can force specific behavior with the `tool_choice` parameter.

1.  **Auto:** (_Default_) Call zero, one, or multiple functions. `tool_choice: "auto"`
2.  **Required:** Call one or more functions. `tool_choice: "required"`
3.  **Forced Function:** Call exactly one specific function. `tool_choice: {"type": "function", "function": {"name": "get_weather"}}`

![Function Calling Diagram Steps](https://cdn.openai.com/API/docs/images/function-calling-diagram-tool-choice.png)

You can also set `tool_choice` to `"none"` to imitate the behavior of passing no functions.

### Parallel function calling

The model may choose to call multiple functions in a single turn. You can prevent this by setting `parallel_tool_calls` to `false`, which ensures exactly zero or one tool is called.

**Note:** Currently, if the model calls multiple functions in one turn then [strict mode](#strict-mode) will be disabled for those calls.

### Strict mode

Setting `strict` to `true` will ensure function calls reliably adhere to the function schema, instead of being best effort. We recommend always enabling strict mode.

Under the hood, strict mode works by leveraging our [structured outputs](/docs/guides/structured-outputs) feature and therefore introduces a couple requirements:

1.  `additionalProperties` must be set to `false` for each object in the `parameters`.
2.  All fields in `properties` must be marked as `required`.

You can denote optional fields by adding `null` as a `type` option (see example below).

Strict mode enabled

```json
{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Retrieves current weather for the given location.",
        "strict": true,
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City and country e.g. Bogotá, Colombia"
                },
                "units": {
                    "type": ["string", "null"],
                    "enum": ["celsius", "fahrenheit"],
                    "description": "Units the temperature will be returned in."
                }
            },
            "required": ["location", "units"],
            "additionalProperties": false
        }
    }
}
```

Strict mode disabled

```json
{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Retrieves current weather for the given location.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City and country e.g. Bogotá, Colombia"
                },
                "units": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "Units the temperature will be returned in."
                }
            },
            "required": ["location"],
        }
    }
}
```

All schemas generated in the [playground](/playground) have strict mode enabled.

While we recommend you enable strict mode, it has a few limitations:

1.  Some features of JSON schema are not supported. (See [supported schemas](/docs/guides/structured-outputs?context=with_parse#supported-schemas).)
2.  Schemas undergo additional processing on the first request (and are then cached). If your schemas vary from request to request, this may result in higher latencies.
3.  Schemas are cached for performance, and are not eligible for [zero data retention](/docs/models#how-we-use-your-data).

Streaming
---------

Streaming can be used to surface progress by showing which function is called as the model fills its arguments, and even displaying the arguments in real time.

Streaming function calls is very similar to streaming regular responses: you set `stream` to `true` and get chunks with `delta` objects.

Streaming function calls

```python
from openai import OpenAI

client = OpenAI()

tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get current temperature for a given location.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City and country e.g. Bogotá, Colombia"
                }
            },
            "required": ["location"],
            "additionalProperties": False
        },
        "strict": True
    }
}]

stream = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "What's the weather like in Paris today?"}],
    tools=tools,
    stream=True
)

for chunk in stream:
    delta = chunk.choices[0].delta
    print(delta.tool_calls)
```

```javascript
import { OpenAI } from "openai";

const openai = new OpenAI();

const tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get current temperature for a given location.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City and country e.g. Bogotá, Colombia"
                }
            },
            "required": ["location"],
            "additionalProperties": false
        },
        "strict": true
    }
}];

const stream = await openai.chat.completions.create({
    model: "gpt-4o",
    messages: [{ role: "user", content: "What's the weather like in Paris today?" }],
    tools,
    stream: true,
    store: true,
});

for await (const chunk of stream) {
    const delta = chunk.choices[0].delta;
    console.log(delta.tool_calls);
}
```

Output delta.tool\_calls

```json
[{"index": 0, "id": "call_DdmO9pD3xa9XTPNJ32zg2hcA", "function": {"arguments": "", "name": "get_weather"}, "type": "function"}]
[{"index": 0, "id": null, "function": {"arguments": "{\"", "name": null}, "type": null}]
[{"index": 0, "id": null, "function": {"arguments": "location", "name": null}, "type": null}]
[{"index": 0, "id": null, "function": {"arguments": "\":\"", "name": null}, "type": null}]
[{"index": 0, "id": null, "function": {"arguments": "Paris", "name": null}, "type": null}]
[{"index": 0, "id": null, "function": {"arguments": ",", "name": null}, "type": null}]
[{"index": 0, "id": null, "function": {"arguments": " France", "name": null}, "type": null}]
[{"index": 0, "id": null, "function": {"arguments": "\"}", "name": null}, "type": null}]
null
```

Instead of aggregating chunks into a single `content` string, however, you're aggregating chunks into an encoded `arguments` JSON object.

When the model calls one or more functions the `tool_calls` field of each `delta` will be populated. Each `tool_call` contains the following fields:

|Field|Description|
|---|---|
|index|Identifies which function call the delta is for|
|id|Tool call id.|
|function|Function call delta (name and arguments)|
|type|Type of tool_call (always function for function calls)|

Many of these fields are only set for the first `delta` of each tool call, like `id`, `function.name`, and `type`.

Below is a code snippet demonstrating how to aggregate the `delta`s into a final `tool_calls` object.

Accumulating tool\_call deltas

```python
final_tool_calls = {}

for chunk in stream:
    for tool_call in chunk.choices[0].delta.tool_calls or []:
        index = tool_call.index

        if index not in final_tool_calls:
            final_tool_calls[index] = tool_call

        final_tool_calls[index].function.arguments += tool_call.function.arguments
```

```javascript
const finalToolCalls = {};

for await (const chunk of stream) {
    const toolCalls = chunk.choices[0].delta.tool_calls || [];
    for (const toolCall of toolCalls) {
        const { index } = toolCall;

        if (!finalToolCalls[index]) {
            finalToolCalls[index] = toolCall;
        }

        finalToolCalls[index].function.arguments += toolCall.function.arguments;
    }
}
```

Accumulated final\_tool\_calls\[0\]

```json
{
    "index": 0,
    "id": "call_RzfkBpJgzeR0S242qfvjadNe",
    "function": {
        "name": "get_weather",
        "arguments": "{\"location\":\"Paris, France\"}"
    }
}
```
