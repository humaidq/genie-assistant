import os
import random
import re
import azure.cognitiveservices.speech as speechsdk
import requests
import threading

directlinebase = "https://directline.botframework.com"
watermark="0"

def request_directline(url, post=False, jsonbody=None):
    headers = { "Authorization": "Bearer " + os.environ.get("DIRECTLINE_KEY") }
    if jsonbody is not None:
        headers["Content-Type"] = "application/json"

    if post:
        return requests.post(directlinebase+"/"+url, headers=headers, json=jsonbody)
    else:
        return requests.get(directlinebase+"/"+url, headers=headers, json=jsonbody)

convID = request_directline("/v3/directline/conversations", post=True).json()["conversationId"]

def get_all_responses():
    global watermark
    resps = []
    activities = request_directline("/v3/directline/conversations/"+convID+"/activities?watermark="+watermark).json()
    for activity in activities["activities"]:
        if activity["from"]["id"] != "1":
            resps.append(activity["text"])
    watermark = activities["watermark"]
    return ". ".join(resps)

def ask_botservice(text):
    message = {
            "type": "message",
            "text": text,
            "from": {
                "id": "1",
                "name": "User"
                }
            }

    request_directline("/v3/directline/conversations/"+convID+"/activities", post=True, jsonbody=message).json()

speech_config = speechsdk.SpeechConfig(subscription=os.environ.get('SPEECH_KEY'), region=os.environ.get('SPEECH_REGION'))
speech_config.speech_recognition_language="en-GB"
speech_config.speech_synthesis_voice_name='en-US-JennyNeural'

audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

def listen():
    print("Speak into your microphone.")
    speech_recognition_result = speech_recognizer.recognize_once_async().get()
 
    if speech_recognition_result.reason == speechsdk.ResultReason.RecognizedSpeech:
        return speech_recognition_result.text
    elif speech_recognition_result.reason == speechsdk.ResultReason.NoMatch:
        print("No speech could be recognized: {}".format(speech_recognition_result.no_match_details))
    elif speech_recognition_result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = speech_recognition_result.cancellation_details
        print("Speech Recognition canceled: {}".format(cancellation_details.reason))
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print("Error details: {}".format(cancellation_details.error_details))
            print("Did you set the speech resource key and region values?")
    return None


def speak(text):
    speech_synthesis_result = speech_synthesizer.speak_text_async(text).get()

    if speech_synthesis_result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print("Speech synthesized for text [{}]".format(text))
    elif speech_synthesis_result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = speech_synthesis_result.cancellation_details
        print("Speech synthesis canceled: {}".format(cancellation_details.reason))
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            if cancellation_details.error_details:
                print("Error details: {}".format(cancellation_details.error_details))
                print("Did you set the speech resource key and region values?")

def gapfiller():
    gapfillers = [
            "Hmm", "Let me think about that", "Good question", "Huh"
            ]
    threading.Thread(target=speak, args=(random.choice(gapfillers),)).start()

regex = r"hey (gene|geanie|jenny|jeannie|jeanne|beijing|jennie)"

def is_prompt(text):
    # normalise the text
    text = text.replace(",", "")
    text = text.replace(".", "")
    text = text.replace("!", "")
    text = text.lower()
    text = text.strip()
    print("Got: " + text)
    if len(re.findall(regex, text)) >0:
        l = re.split(regex, text)
        print( l)
        if len(l) >1:
            return (True, l[2].strip())
        else:
            return (True, "")
    return (False, "")

while True:
    print("Waiting for prompt")
    text = listen()
    if text is None:
        continue
    prompt = is_prompt(text)
    if not prompt[0]:
        continue

    print(prompt)
    if len(prompt[1]) > 1:
        gapfiller()
        ask_botservice(text.strip())
        speak(get_all_responses())
    else:
        speak("Yes?")
        print("Listening for question") 
        text = listen()
        if text is None:
            speak("I didn't quite get that.")
            continue
        print("Got Question: " + text)
        gapfiller()
        ask_botservice(text.strip())
        speak(get_all_responses())
