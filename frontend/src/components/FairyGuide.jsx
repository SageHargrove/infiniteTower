import React, { useState, useEffect } from 'react'
import FairyTip from './FairyTip'

export default function FairyGuide({ floor, lastResult, fairyGender, highestFloor }) {
  const [show, setShow] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    let timer

    const evaluateTriggers = async () => {
      let triggered = false
      // floor starts at 1 as a transient default before real save progress
      // loads, so this must also check highestFloor — otherwise it re-fires
      // on every page mount even deep into a run, during the brief window
      // before selectedFloor auto-advances past 1.
      if (floor === 1 && !highestFloor && !lastResult) {
        setMessage("Welcome to the Hollow Spire! Assemble your heroes and let's clear the first floor!")
        triggered = true
      } else if (floor === 20 && !lastResult) {
        setMessage("Floor 20 is a Raid Boss! All your teams will combine to fight a single massively overpowered enemy!")
        triggered = true
      } else if (floor === 21 && !lastResult) {
        setMessage("From here on out, we need multiple teams. Your teams will fight parallel battles!")
        triggered = true
      } else if (lastResult && lastResult.winner === "enemies") {
        setMessage("Oh no, your team was defeated! Remember to check your gear and hero synergies before trying again.")
        triggered = true
      } else if (lastResult && lastResult.winner === "heroes" && lastResult.combat?.dead_heroes?.length > 0) {
        setMessage("We won, but some heroes fell... their trauma and stress will increase. Let them rest!")
        triggered = true
      }

      if (triggered) {
        setShow(true)
        timer = setTimeout(() => setShow(false), 10000)
      }
    }

    evaluateTriggers()

    return () => clearTimeout(timer)
  }, [floor, lastResult, highestFloor])

  return <FairyTip show={show} message={message} fairyGender={fairyGender} onDismiss={() => setShow(false)} />
}
