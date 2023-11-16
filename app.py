from openai import OpenAI
import time
import streamlit as st


def main():
    st.set_page_config(
        page_title="OpenAI Assistant with Retrieval",
        page_icon="📚",
    )

    api_key = st.secrets["OPENAI_API_KEY"]
    assistant_id = st.secrets["ASSISTANT_ID"]

    # Initiate st.session_state
    st.session_state.client = OpenAI(api_key=api_key)

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "start_chat" not in st.session_state:
        st.session_state.start_chat = False

    if st.session_state.client:
       st.session_state.start_chat = True

    if st.session_state.start_chat:
        # Display existing messages in the chat
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

                # Accept user input
        if prompt := st.chat_input(f"Message for more Greek recipes..."):
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            # Display user message in chat message container
            with st.chat_message("user"):
                st.markdown(prompt)

            # Create a thread
            st.session_state.thread = st.session_state.client.beta.threads.create()

            # Add a Message to the thread
            st.session_state.client.beta.threads.messages.create(
                thread_id=st.session_state.thread.id,
                role="user",
                content=prompt,
            )

            # As of now, assistant and thread are not associated to eash other
            # You need to create a run in order to tell the assistant at which thread to look at
            run = st.session_state.client.beta.threads.runs.create(
                thread_id=st.session_state.thread.id,
                assistant_id=assistant_id,
            )

            # with while loop continuously check the status of a run until it neither 'queued' nor 'in progress'
            def wait_for_complete(run, thread):
                while run.status == "queued" or run.status == "in_progress":
                    run = st.session_state.client.beta.threads.runs.retrieve(
                        thread_id=thread.id,
                        run_id=run.id,
                    )
                    time.sleep(0.5)
                return run

            run = wait_for_complete(run, st.session_state.thread)

            # once the run has completed, list the messages in the thread -> they are ordered in reverse chronological order
            replies = st.session_state.client.beta.threads.messages.list(
                thread_id=st.session_state.thread.id
            )

            # This function will parse citations and make them readable
            def process_replies(replies):
                citations = []

                # Iterate over all replies
                for r in replies:
                    if r.role == "assistant":
                        message_content = r.content[0].text
                        annotations = message_content.annotations

                        # Iterate over the annotations and add footnotes
                        for index, annotation in enumerate(annotations):
                            # Replace the text with a footnote
                            message_content.value = message_content.value.replace(
                                annotation.text, f" [{index}]"
                            )

                            # Gather citations based on annotation attributes
                            if file_citation := getattr(
                                annotation, "file_citation", None
                            ):
                                cited_file = st.session_state.client.files.retrieve(
                                    file_citation.file_id
                                )
                                citations.append(
                                    f"[{index}] {file_citation.quote} from {cited_file.filename}"
                                )
                            elif file_path := getattr(annotation, "file_path", None):
                                cited_file = st.session_state.client.files.retrieve(
                                    file_path.file_id
                                )
                                citations.append(
                                    f"[{index}] Click <here> to download {cited_file.filename}"
                                )

                # Combine message content and citations
                full_response = message_content.value + "\n" + "\n".join(citations)
                return full_response

            # Add the processed response to session state
            processed_response = process_replies(replies)
            st.session_state.messages.append(
                {"role": "assistant", "content": processed_response}
            )
            # Display assistant response in chat message container
            with st.chat_message("assistant"):
                st.markdown(processed_response, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
