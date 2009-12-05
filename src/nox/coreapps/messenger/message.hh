#ifndef MESSAGE_HH__
#define MESSAGE_HH__

/** Types of messages.
 * Type value 0x00 to 0x09 are reserved for internal use.
 */
enum msg_type
{
  /** Disconnection message.
   * Need to be consistent.
   */
  MSG_DISCONNECT = 0x00,
  /** Echo message.
   * Need to be consistent.
   */
  MSG_ECHO = 0x01,
  /** Response message.
   * Need to be consistent.
   */
  MSG_ECHO_RESPONSE = 0x02,
  /** Authentication.
   * Need to be consistent.
   */
  MSG_AUTH = 0x03,
  /** Authenication response.
   * Need to be consistent.
   */
  MSG_AUTH_RESPONSE = 0x04,
  /** Authentication status.
   * Need to be consistent.
   */
  MSG_AUTH_STATUS = 0x05,

  /** Plain string.
   */
  MSG_STRING = 0x0A,
};

/** \brief Basic structure of message in \ref vigil::messenger.
 *
 * Copyright (C) Stanford University, 2008.
 * @author ykk
 * @date December 2008
 * @see messenger
 */
struct messenger_msg
{
  /** Length of message, including this header.
   */
  uint16_t length;
  /** Type of message, as defined in \ref msg_type.
   */
  uint8_t type;
  /** Reference to body of message.
   */
  uint8_t body[0];
} __attribute__ ((packed));

#endif
